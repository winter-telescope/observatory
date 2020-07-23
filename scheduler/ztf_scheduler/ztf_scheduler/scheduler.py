# https://gist.github.com/jbn/fc90e3ddbc5c60c698d07b3df30004c8
import configparser
from collections import defaultdict
import asyncio
from aiohttp import web
import numpy as np
from astropy.time import Time
import astropy.coordinates as coord
import astropy.units as u
from astroplan import download_IERS_A
import logging
import logging.config
from ztf_sim.Scheduler import Scheduler
from ztf_sim.QueueManager import QueueEmptyError, ListQueueManager
from ztf_sim.utils import RA_to_HA, skycoord_to_altaz, block_index
from ztf_sim.constants import P48_loc
from ztf_sim.configuration import Configuration
from .constants import BASE_DIR, TARGET_OUTPUT_DIR
from .constants import ROZ_FILTER_NAME_TO_ID, FILTER_ID_TO_ROZ_NAME, TESTING
from .constants import UTCFormatter, LOGGING

async def scheduler_update(scheduler):
    """Main loop that updates the queue according to the clock."""
    interval = 10

    mjd_today = 0

    while True:
        try:
            await asyncio.sleep(interval)

            
            # TODO: block recomputes, when needed

            # perform nightly recomputes at midnight UTC, which is always before
            # sunset in Pasadena
            # TODO: clear out old alternate queues?
            time_now = Time.now()
            mjd_now = np.floor(time_now.mjd).astype(int)

            if (mjd_now > mjd_today) and not TESTING:
                mjd_today = mjd_now

                # only download IERS-A in daytime
                dayfrac = time_now.mjd - mjd_today
                # eariliest sunset is 00:40 UTC, latest sunrise is ~14:10 UTC
                if (dayfrac < 30./(24.*60.)) or (dayfrac > 14.25/24.):    
                    try:
                        download_IERS_A()
                    except Exception as e:
                        logging.exception(e)

                try:
                    scheduler.remove_empty_and_expired_queues(time_now)
                except Exception as e:
                    logging.exception(e)

                # Look for timed queues that will be valid tonight, 
                # to exclude from the nightly solution
                block_use = scheduler.find_block_use_tonight(time_now)
                timed_obs_count = scheduler.count_timed_observations_tonight()

                logging.info(f'Block use by timed queues: {block_use}')

                logging.info('Assigning nightly requests')
                time_now.location = P48_loc
                current_state_dict = {'current_time': time_now}
                try:
                    scheduler.queues['default'].assign_nightly_requests(
                        current_state_dict,
                        scheduler.obs_log, time_limit=15.*u.minute, 
                        block_use = block_use,
                        timed_obs_count = timed_obs_count)
                    logging.info('Nightly requests ready')
                except NotImplementedError:
                    logging.warning('Automatic nightly requests not implemented for this queue!')

            last_queue = scheduler.Q.queue_name
            scheduler.check_for_TOO_queue_and_switch(time_now)
            scheduler.check_for_timed_queue_and_switch(time_now)
            next_queue = scheduler.Q.queue_name
            if next_queue != last_queue:
                logging.info(f'Switching to queue {next_queue}')


        except Exception as e:
            # So you can observe on disconnects and such.
            logging.exception(e)
            raise

    return


async def next_obs_handler(request):
    """When requested, send next observation details to the robot."""
    data = await request.json()

    if TESTING:
        current_state_dict = make_testing_current_state_dict()
    else:
        # TODO -- test if the reported current state is stale
        current_state_dict = request.app['current_state_dict']
        # force it to use the current time
        time_now = Time.now()
        time_now.location=P48_loc
        current_state_dict['current_time'] = time_now

    try:
        next_obs = request.app['scheduler'].Q.next_obs(current_state_dict,
                request.app['scheduler'].obs_log)
    except QueueEmptyError:

        # if the current queue is empty and not the default, 
        # switch back to default
        if request.app['scheduler'].Q.queue_name != 'default':
            logging.info('Current queue returned QueueEmptyError! Switching to default')
            request.app['scheduler'].set_queue('default')

            try:
                next_obs = request.app['scheduler'].Q.next_obs(current_state_dict,
                        request.app['scheduler'].obs_log)
            except QueueEmptyError:
                # use the fallback program below
                next_obs = None
            except Exception as e:
                logging.error('Failed getting next default observation!')
                logging.exception(e)
                next_obs = None
        else:
            next_obs = None # we're in the default Queue and it's empty
        
        if next_obs is None:
            if  ('fallback' in request.app['scheduler'].queues):
                logging.warning('Queue returned QueueEmptyError! Trying fallback queue')
                try:
                    next_obs = request.app['scheduler'].queues['fallback'].next_obs(
                        current_state_dict, request.app['scheduler'].obs_log)
                except Exception as e:
                    logging.error('Failed getting fallback observation!')
                    logging.exception(e)
                    return web.Response(status=404)
            else:
                logging.error('No fallback queue available!')
                return web.Response(status=404)

    except Exception as e:
        logging.error('Failed getting next observation!')
        logging.exception(e)
        return web.Response(status=500)

    logging.info(next_obs)

    # check if requested filter is available
    if next_obs['target_filter_id'] not in request.app['filters_available']:

        logging.error('Queue requested unavailable filter id {}! Available filters: {}'.format(next_obs['target_filter_id'], request.app['filters_available']))
        # TODO: feed back to scheduler and resolve with available filters
        
        # For now, proceed with the requested observation in the current filter
        logging.warning('Replacing unavailable filter {} for request {} with current filter {}'.format(
            next_obs['target_filter_id'], next_obs['request_id'], 
            request.app['current_state_dict']['current_filter_id']))
        next_obs['target_filter_id'] = request.app['current_state_dict']['current_filter_id']
        
        

    # write queue_target.dat
    with open(TARGET_OUTPUT_DIR+'queue_target.dat','w') as f:
        f.write(f"PROGRAM_PI={next_obs['target_program_pi']}\n")
        f.write(f"PROGRAM_ID={next_obs['target_program_id']}\n")
        # pad field id with zeros--can't use string formatting
        field_id_str = str(next_obs['target_field_id'])
        f.write(f"FIELD_ID={field_id_str.zfill(6)}\n")
        f.write(f"REQUEST_ID={next_obs['request_id']}\n")
        f.write(f"COMMENT={next_obs['target_subprogram_name']}\n")
        sc = coord.SkyCoord(next_obs['target_ra'], next_obs['target_dec'], 
                frame='icrs', unit=u.deg)
        radec_string = sc.to_string(style='hmsdms',sep=':',precision=2)
        ras,decs = radec_string.split()
        f.write(f"OBJ_RA={ras}\n")
        f.write(f"OBJ_DEC={decs}\n")
        f.write("EQUINOX=2000.0\n")
        f.write("RA_RATE=0.0\n")
        f.write("DEC_RATE=0.0\n")
        f.write(f"EXPTIME={next_obs['target_exposure_time'].to(u.second).value}\n")
        f.write(f"FILTER={FILTER_ID_TO_ROZ_NAME[next_obs['target_filter_id']]}\n")

    # save next_obs until we get the completion response
    request.app['pending_obs'][next_obs['request_id']] = next_obs

    #if len(request.app['pending_obs']) >= 3:
    logging.info(f"{len(request.app['pending_obs'])} observations pending status: {list(request.app['pending_obs'].keys())}")

    # remove from request sets
    try:
        request.app['scheduler'].queues[next_obs['queue_name']].remove_requests(
                next_obs['request_id'])
    except Exception as e:
        logging.exception(e)

    return web.Response(status=200)

async def obs_status_handler(request):
    """Process robot's report that the observation succeeded or failed."""
    data = await request.json()
    logging.info(data)

    #TODO: check that request_id in data
    if 'request_id' not in data:
        logging.error("observation_status does not have request_id")
        return web.Response(status=400)

    # this shouldn't be happen, but if ROS sends extra status
    # commands we should just bail out
    if len(request.app['pending_obs']) == 0:
        return web.Response(status=200)

    # if status is good, log the observation
    if data['status'] == 0:
        if data['request_id'] not in request.app['pending_obs']:
            logging.warning(f"Request_id {data['request_id']} not in pending observations")
            return web.Response(status=200)

        # wrap the logging in try/except, otherwise we will repeat
        # on the same field indefinitely.  Will cause trouble downstream however
        try:
            # store in observing database
            # logger wants the current time
            # TODO: this isn't the right way to get the obs time
            state = request.app['current_state_dict']
            time_now = Time.now()
            time_now.location=P48_loc
            state['current_time'] = time_now
            request.app['scheduler'].obs_log.log_pointing(
                    state, request.app['pending_obs'][data['request_id']])
        except Exception as e:
            logging.exception(e)


    else:
        # Observation failed!  
        logging.error(f"Request {data['request_id']} not observed!")
        # TODO: create a failed history log

    # remove from pending obs
    _ = request.app['pending_obs'].pop(data['request_id'], None)

    return web.Response(status=200)


async def reload_queue_handler(request):
    """Reload the queue if requested by the robot."""
    data = await request.json()
    logging.info(data)

    #TODO: actually reload the queue

    return web.Response(status=200)

async def filter_fixed_handler(request):
    """Respond to the robot's report of which filters are available."""
    data = await request.json()
    logging.info(data)

    if ((data['fixed_filter'] not in ROZ_FILTER_NAME_TO_ID) and
        (data['fixed_filter'] != 'all_filters')): 
        logging.error(f"Request to fix filter to {data['fixed_filter']} is malformed")
        return web.Response(status=400)

    if data['fixed_filter'] == 'all_filters':
        request.app['filters_available'] = request.app['ALL_FILTER_IDS']
    else:
        request.app['filters_available'] = (ROZ_FILTER_NAME_TO_ID[data['fixed_filter']],)


    return web.Response(status=200)

async def current_state_handler(request):
    """Store the robot's information about the current state."""
    data = await request.json()
    logging.info(data)

    # TODO: detect and handle equinox other than J2000.

    sc = coord.SkyCoord(data['ra'], data['dec'], frame='icrs', 
            unit=(u.hourangle, u.deg))
    time_now = Time.now()
    time_now.location = P48_loc

    if (data['filter'] not in ROZ_FILTER_NAME_TO_ID):
        return web.Response(status=400)
    if ((data['ra'] < 0.) or (data['ra'] > 24.)):
        return web.Response(status=400)
    if ((data['dec'] < -90.) or (data['dec'] > 90.)):
        return web.Response(status=400)


    current_state_dict = {'current_time': time_now,
                'current_ha': RA_to_HA(data['ra'] * u.hourangle, time_now),
                'current_dec': data['dec'] * u.degree,
                'current_domeaz': skycoord_to_altaz(sc, time_now).az,
                'current_filter_id': ROZ_FILTER_NAME_TO_ID[data['filter']],    
                # TODO: consider updating seeing
                'current_zenith_seeing': 2.0 * u.arcsec,
                'filters': request.app['filters_available'],
                # 'target_skycoord' only needed by the simulator state machine
                'target_skycoord':  sc,
                'time_state_reported': time_now}



    request.app['current_state_dict'] = current_state_dict

    return web.Response(status=200)

async def switch_queue_handler(request):
    """switch to a new named queue, potentially with a different queue manager."""
    data = await request.json()
    logging.info(data)

    if 'queue_name' not in data:
        logging.error(f"Missing queue_name argument to switch_queue.")
        return web.Response(status=400)

    if data['queue_name'] not in request.app['scheduler'].queues:
        logging.error(f"Requested queue {data['queue_name']} does not exist")
        return web.Response(status=400)

    request.app['scheduler'].set_queue(data['queue_name'])

    return web.Response(status=200)

def validate_list_queue(target_dict_list):

    for target in target_dict_list:
        print(target)
        required_columns = ['field_id','program_id', 'subprogram_name',
                'filter_id', 'program_pi']
        for col in required_columns:
            if col not in target:
                logging.error(f'Missing required column {col}')
                return False
        if (target['filter_id'] not in FILTER_ID_TO_ROZ_NAME.keys()):
            logging.error(f"Bad filter specified: {target['filter_id']}")
            return False
        if 'ra' in target:
            if ((target['ra'] < 0.) or (target['ra'] > 360.)):
                logging.error(f"Bad ra: {target['ra']}")
                return False
            if 'dec' not in target:
                logging.error(f"Has ra, missing dec")
                return False
        if 'dec' in target:
            if ((target['dec'] < -90.) or (target['dec'] > 90.)):
                logging.error(f"Bad dec: {target['dec']}")
                return False
            if 'ra' not in target:
                logging.error(f"Has dec, missing ra")
                return False

    return True



async def add_queue_handler(request):
    """Add a queue."""
    data = await request.json()
    logging.info(data)
    print(data["targets"])

    if "queue_name" not in data:
        logging.error("No queue_namespecified")
        return web.Response(status=400)

    if "queue_type" not in data:
        logging.error("No queue_type specified")
        return web.Response(status=400)

    if data["queue_type"] != 'list':
        logging.error("Only list queues are implemented")
        return web.Response(status=400)

    # check if the queue already exists--don't replace it if so
    # (PUT should be idempotent)
    if data['queue_name'] in request.app['scheduler'].queues:
        msg = f"Provided queue {data['queue_name']} already exists"
        logging.info(msg)
        return web.Response(status=200, text=msg)

    try:
        queue = load_list_queue(data)
        request.app['scheduler'].add_queue(data["queue_name"], queue)
    except Exception as e:
        logging.exception(e)
        return web.Response(status=400)

    # if no validity window is specified, switch immediately
    if (("validity_window_mjd" not in data) or 
        (data["validity_window_mjd"] is None)): 
        try:
            request.app['scheduler'].set_queue(data['queue_name'])
        except Exception as e:
            logging.exception(e)
            return web.Response(status=400)

    return web.Response(status=200)


def load_list_queue(data):
    """Helper function to construct a list queue."""

    # don't await here since we call from add_queue_handler
    print(data["targets"])

    if "queue_name" not in data:
        data["queue_name"] = "list_queue"

    if not validate_list_queue(data['targets']):
        raise ValueError("Supplied list queue did not validate!")

    # make a fake QueueConfiguration
    queue_config = Configuration(None)
    queue_config.config = data
    queue_config.config['queue_manager'] = 'list'

    return ListQueueManager(data["queue_name"], queue_config)

async def current_queue_status_handler(request):
    """Return current queue status"""

    s = request.app['scheduler']

    data = {'queue_name': s.Q.queue_name,
             'queue_type': s.Q.queue_type,
             'is_current': True,
             'validity_window_mjd': s.Q.validity_window_mjd(),
             'is_valid': s.Q.is_valid(Time.now()),
             'is_TOO': s.Q.is_TOO,
             'queue': s.Q.return_queue().to_json(orient='records')}

    return web.json_response(data)

async def queue_status_handler(request):
    """Return queue status"""
    data = await request.json()
    logging.info(data)

    s = request.app['scheduler']

    if 'queue_name' in data:
        n = data['queue_name']
        if n not in s.queues:
            return web.Response(status=404)
        is_current = (n == s.Q.queue_name)
        response = {'queue_name': s.queues[n].queue_name, 
                  'queue_type': s.queues[n].queue_type,
                  'is_current': is_current,
                  'validity_window_mjd': s.queues[n].validity_window_mjd(),
                  'is_valid': s.queues[n].is_valid(Time.now()),
                  'is_TOO': s.queues[n].is_TOO,
                  'queue': s.queues[n].return_queue().to_json(orient='records')}
    else:
        response = [{'queue_name': qq.queue_name, 'queue_type': qq.queue_type,
                   'is_current': (qq.queue_name == s.Q.queue_name),
                   'validity_window_mjd': qq.validity_window_mjd(),
                   'is_valid': qq.is_valid(Time.now()), 'is_TOO': qq.is_TOO,
                   'queue': qq.return_queue().to_json(orient='records')}
                   for name, qq in s.queues.items()]


    return web.json_response(response)

async def delete_queue_handler(request):
    """Return queue status"""
    data = await request.json()
    logging.info(data)

    s = request.app['scheduler']

    if 'queue_name' not in data:
        return web.Response(status=400)

    # don't allow deleting the default or fallback queue
    if data['queue_name'] in ['default','fallback']:
        return web.Response(status=403)

    try:
        s.delete_queue(data['queue_name'])
    except Exception as e:
        logging.exception(e)
        return web.Response(status=400)

    return web.Response(status=200)

async def obs_history_handler(request):
    """Returns observations on a given date
    takes optional argument 'date': astropy.time.Time-compatible string 
    (e.g., 2018-01-01)"""

    data = await request.json()
    if 'date' in data:
        try:
            t = Time(data['date'])
            # sanity checks
            assert(t > Time('2018-01-01'))
            assert(t < Time('2022-01-01'))
        except Exception as e:
            logging.exception(e)
            return web.Response(status=400)
    else:
        t = Time.now()

    history = request.app['scheduler'].obs_log.return_obs_history(t)

    if len(history) == 0:
        response = {'history':[]}
        return web.json_response(response)

    # make ra and dec degrees
    history['field_ra'] = np.degrees(history['fieldRA'])
    history['field_dec'] = np.degrees(history['fieldDec'])

    history.drop(['fieldRA','fieldDec'], axis=1, inplace=True)

    # match input style
    history.rename(index=str, columns = {'requestID':'request_id',
        'propID':'program_id', 'fieldID': 'field_id',
        'filter': 'filter_id', 'expMJD':'exposure_mjd', 
        'visitExpTime': 'exposure_time', 'subprogram':'subprogram_name'},
        inplace=True)

    response = {'history':history.to_json(orient='records')}
    return web.json_response(response)

async def set_validity_window_handler(request):
    """(Re)set a queue's validity window"""
    data = await request.json()
    logging.info(data)

    s = request.app['scheduler']

    if 'queue_name' not in data:
        return web.Response(status=400)

    if 'validity_window' not in data:
        return web.Response(status=400)

    if len(data['validity_window']) != 2:
        return web.Response(status=400)


    # don't allow adjusting the default or fallback queue
    if data['queue_name'] in ['default','fallback']:
        return web.Response(status=403)

    n = data['queue_name']
    if n not in s.queues:
        return web.Response(status=404)
    s.queues[n].set_validity_window_mjd(data['validity_window'][0],
        data['validity_window'][1])

    return web.Response(status=200)

async def aio_scheduler_status_handler(request):
    """Status monitor"""
    # http://HOST:PORT/?interval=90
    interval = int(request.GET.get('interval', 1))

    # Without the Content-Type, most (all?) browsers will not render
    # partially downloaded content. Note, the response type is
    # StreamResponse not Response.
    resp = web.StreamResponse(status=200,
                              reason='OK',
                              headers={'Content-Type': 'text/html'})

    # The StreamResponse is a FSM. Enter it with a call to prepare.
    await resp.prepare(request)



    while True:
        try:
            resp.write(' {} {} |'.format(
                request.app['myobj'].letters, 
                request.app['myobj'].numbers).encode('utf-8'))

            # Yield to the scheduler so other processes do stuff.
            await resp.drain()

            # This also yields to the scheduler, but your server
            # probably won't do something like this.
            await asyncio.sleep(interval)
        except Exception as e:
            # So you can observe on disconnects and such.
            logging.exception(e)
            raise

    return resp
 


async def build_server(address, port, ALL_FILTER_IDS, scheduler):
    # For most applications -- those with one event loop -- 
    # you don't need to pass around a loop object. At anytime, 
    # you can retrieve it with a call to asyncio.get_event_loop(). 
    # Internally, aiohttp uses this pattern a lot. But, sometimes 
    # "explicit is better than implicit." (At other times, it's 
    # noise.) 
    loop = asyncio.get_event_loop()
    app = web.Application(loop=loop)
    # these are the ROS methods
    app.router.add_route('PUT', "/next_obs", next_obs_handler)
    app.router.add_route('PUT', "/obs_status", obs_status_handler)
    app.router.add_route('PUT', "/reload_queue", reload_queue_handler)
    app.router.add_route('PUT', "/filter_fixed", filter_fixed_handler)
    app.router.add_route('PUT', "/current_state", current_state_handler)
    # these are externally visible
    app.router.add_route('PUT', "/current_queue", switch_queue_handler)
    app.router.add_route('GET', "/current_queue", current_queue_status_handler)
    app.router.add_route('PUT', "/queues", add_queue_handler)
    app.router.add_route('GET', "/queues", queue_status_handler)
    app.router.add_route('DELETE', "/queues", delete_queue_handler)
    app.router.add_route('GET', "/obs_history", obs_history_handler)
    app.router.add_route('PUT', "/validity_window", set_validity_window_handler)
    app['scheduler'] = scheduler
    time_now = Time.now()
    time_now.location = P48_loc
    app['current_state_dict'] =  {'current_time': time_now}
    app['pending_obs'] = {}
    app['ALL_FILTER_IDS'] = ALL_FILTER_IDS
    app['filters_available'] = app['ALL_FILTER_IDS']
    
    return await loop.create_server(app.make_handler(), address, port)

def make_testing_current_state_dict():
    assert TESTING

    testing_ra = 21.
    testing_dec = 33. * u.degree
    testing_time = Time('2017-10-03 03:00:00', scale='utc', location=P48_loc)
    sc = coord.SkyCoord(testing_ra, testing_dec, frame='icrs',
        unit=(u.hourangle, u.deg))

    current_state_dict = {'current_time': testing_time,
            'current_ha': RA_to_HA(testing_ra* u.deg, testing_time),
            'current_dec': testing_dec,
            'current_domeaz': skycoord_to_altaz(sc, testing_time).az,
            'current_filter_id': 2,
            'current_zenith_seeing': 2.0 * u.arcsec,
            'filters': [1,2,3],
            'target_skycoord':  sc,
            'time_state_reported': testing_time}

    return current_state_dict


def main():

    logging.config.dictConfig(LOGGING)

    op_config_file_fullpath  = BASE_DIR + '../../ztf_survey_configuration/schedule_config.json'
    run_config_file_fullpath = BASE_DIR + '../config/default.cfg'

    run_config = configparser.ConfigParser()
    run_config.read(run_config_file_fullpath)
    HOST = run_config['server']['HOST']
    PORT = run_config['server'].getint('PORT')
    ALL_FILTER_IDS = eval(run_config['scheduler']['ALL_FILTER_IDS'])

    scheduler = Scheduler(op_config_file_fullpath, run_config_file_fullpath)

    # TODO: need a function to call to populate this correctly
    if TESTING:
        logging.warning('***WARNING: QUEUE SET TO TEST MODE, NOT USING CURRENT TIME***')
        current_state_dict = make_testing_current_state_dict()

        logging.info('Assigning nightly requests')
        try:
            scheduler.queues['default'].assign_nightly_requests(
                current_state_dict, scheduler.obs_log)
            logging.info('Nightly requests ready')
        except NotImplementedError:
            logging.warning('Automatic nightly requests not implemented for this queue!')
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(build_server(HOST, PORT, ALL_FILTER_IDS, scheduler))
    logging.info("Server ready!")

    task = loop.create_task(scheduler_update(scheduler))
    
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        logging.info("Shutting Down!")
        # Canceling pending tasks and stopping the loop
        asyncio.gather(*asyncio.Task.all_tasks()).cancel()
        loop.stop()
        loop.close()
