"""Implementation of core scheduling algorithms using Gurobi."""

import os
from collections import defaultdict
from gurobipy import *
import numpy as np
import shelve
import astropy.units as u
import pandas as pd
from collections import defaultdict
from .constants import TIME_BLOCK_SIZE, EXPOSURE_TIME, READOUT_TIME, FILTER_CHANGE_TIME

#s = shelve.open('tmp_vars.shelf',flag='r')
#df_metric = s['block_slot_metric']
#df = s['df']
#
#requests_allowed = {1: 548, 2: 548, 3: 274}

max_exps_per_slot = np.ceil((TIME_BLOCK_SIZE / 
                (EXPOSURE_TIME + READOUT_TIME)).to(
                u.dimensionless_unscaled).value).astype(int)

def night_optimize(df_metric, df, requests_allowed, time_limit=30*u.second,
        block_use = defaultdict(float)):
    """Determine which requests to observe and in what slots.

    Decision variable is yes/no per request_id, slot, filter,
    with an additional decision variable on which filter to use in which slot
    and another for which request sets are observed at all."""

    # these are fragile when columns get appended
    slots = np.unique(df_metric.columns.get_level_values(0).values)
    filter_ids = np.unique(df_metric.columns.get_level_values(1).values)
    # extra columns floating around cause problems
    filter_ids = [fid for fid in filter_ids if fid != '']

    # flatten the metric dataframe to make it easier to work with 
    df_metric_local = df_metric.copy()
    df_metric_local['request_id'] = df_metric_local.index

    # make a "tidy" dataframe with one row per (request, slot, filter)
    dft = pd.melt(df_metric_local,id_vars='request_id',
        var_name=['slot','metric_filter_id'],
        value_name='metric')
    # get n_reqs by fid
    n_reqs_cols = ['n_reqs_{}'.format(fid) for fid in filter_ids]
    n_reqs_cols.extend(['program_id','subprogram_name',
        'total_requests_tonight','exposure_time'])
    dft = pd.merge(dft,df[n_reqs_cols],left_on='request_id',right_index=True)

    # TEMPORARY: force ZUDS to use 90s i-band exposures
    # wZUDSi = (dft['subprogram_name'] == 'ZUDS') & (dft['metric_filter_id'] == 3)
    # dft.loc[wZUDSi,'exposure_time'] = 90.

    # calculate number of slots required per request set
    
    # nreqs_{fid} weighted sum over the filters
    for fid in filter_ids:
        wfid = dft['metric_filter_id'] == fid
        n_req_col = 'n_reqs_{}'.format(fid)
        dft.loc[wfid, 'metric'] *= (dft.loc[wfid, n_req_col] /
            dft.loc[wfid, 'total_requests_tonight'])
    grprs = dft.groupby(['request_id','slot'])
    dfrs = grprs['metric'].agg(np.sum)

    # calculate n_usable slots
    grpr = dfrs.groupby('request_id')
    n_usable = grpr.agg(lambda x: np.sum(x > 0.05)).astype(int)
    n_usable.name = 'n_usable'

    # sum df_metric down to one column
    metric_sum = grpr.agg(lambda x: np.sum(np.where(x > 0, x, 0)))
    metric_sum.name = 'metric_sum'

    # merge additional useful info
    dfr = df[['program_id','subprogram_name','total_requests_tonight']].join(n_usable).join(metric_sum)

    # determine which request sets have enough usable slots
    dfr['observable_tonight'] = dfr['total_requests_tonight'] <= dfr['n_usable']
 
    # restrict to only the observable requests
    dfr = dfr[dfr['observable_tonight']]
    dft = pd.merge(dft,dfr[['n_usable','observable_tonight']],
            left_on='request_id',right_index=True)
    request_sets = dfr.index.values
    df_metric = df_metric.loc[dfr.index]

    # Create an empty model
    m = Model('slots')

    # set the number of threads Gurobi uses
    if 'GRB_USE_NTHREADS' in os.environ:
        m.Params.Threads = int(os.environ['GRB_USE_NTHREADS'])

    # decision variable: yes or no for each request set
    yr_dict = m.addVars(df_metric_local.index,name='Yr',vtype=GRB.BINARY)
    yr_series = pd.Series(yr_dict,name='Yr')
    dfr = dfr.join(yr_series)


    yrtf_dict = m.addVars(dft.index,name='Yrtf',vtype=GRB.BINARY)
    yrtf_series = pd.Series(yrtf_dict,name='Yrtf')
    dft = dft.join(yrtf_series)
    
    # W debug
    # dft.to_csv('~/Desktop/dft_debug_before.csv')
    
    # Trying to make this construction faster
    # print('dft len before', len(dft))
    cut = dft['metric'] > 0
    dft = dft[cut]
    # print('dft len after', len(dft))
    
    
    # create resultant variables: Yr = 1 if request r is observed in at least
    # one slot
    for r in request_sets:
        m.addGenConstrOr(yr_dict[r], dft.loc[dft['request_id'] == r, 'Yrtf'],
                "orconstr_{}".format(r))

    new_index = pd.MultiIndex.from_arrays([dft.request_id, dft.slot])
    new_values = np.array([np.array(dft.metric_filter_id), np.array(dft.n_reqs_1), np.array(dft.n_reqs_2), np.array(dft.n_reqs_3), np.array(dft.Yrtf)]).T
    dft_new = pd.DataFrame(new_values, columns=['metric_filter_id', 'n_reqs_1', 'n_reqs_1', 'n_reqs_3', 'Yrtf'], index=new_index)
    
    def sum_finder(f,r):
        #temp_sum = np.sum(dft.loc[(dft['request_id'] == r) & (dft['metric_filter_id'] == f), 'Yrtf'])
        temp_dft = dft_new.loc[r]
        temp_sum = np.sum(temp_dft.loc[temp_dft['metric_filter_id'] == f, 'Yrtf'])
        return temp_sum
        
    def nreqs_sum(f,r):
        temp_nreqs = df.loc[r,'n_reqs_{}'.format(f)] * dfr.loc[r,'Yr']
        return temp_nreqs
    
    # nreqs_{fid} slots assigned per request set if it is observed
    # this constructor is pretty slow
    constr_nreqs = m.addConstrs((sum_finder(f,r) == nreqs_sum(f,r) for f in filter_ids for r in request_sets), "constr_nreqs")
    
    # constr_nreqs = m.addConstrs(
    # ((np.sum(dft.loc[(dft['request_id'] == r) &
                    # (dft['metric_filter_id'] == f), 'Yrtf'])
                    # == (df.loc[r,'n_reqs_{}'.format(f)] * dfr.loc[r,'Yr']))
                    # for f in filter_ids for r in request_sets),
                    # "constr_nreqs")
    
    # create resultant variables: Ytf = 1 if slot t has filter f used
    ytf = m.addVars(slots, filter_ids, vtype=GRB.BINARY)
    for t in slots:
        for f in filter_ids:
            m.addGenConstrOr(ytf[t,f], 
                dft.loc[(dft['slot'] == t) &
                        (dft['metric_filter_id'] == f), 'Yrtf'], #tolist() 
                        "orconstr_{}_{}".format(t,f))

    # now constrain ourselves to one and only one filter per slot.  
    constr_onefilter = m.addConstrs(
        (ytf.sum(t,'*') <= 3 for t in slots), 'constr_onefilter')

    # create filter change resultant variable: Ydfds = 1 if
    # filter changes between slot s and s+1
    ydfds = m.addVars(slots[:-1], vtype=GRB.BINARY)
    # use indicator constraints to set the value
    for i,t in enumerate(slots[:-1]):
        for f in filter_ids:
            m.addGenConstrIndicator(ydfds[t], False,
                ytf[slots[i],f] - ytf[slots[i+1], f], GRB.EQUAL, 0,
                        "filt_change_indicator_{}_{}".format(t,f))
    

    # total exposure time constraint 
    constr_nperslot = m.addConstrs(
        ((np.sum(dft.loc[dft['slot'] == t, 'Yrtf'] * 
            (dft.loc[dft['slot'] == t, 'exposure_time'] + 
                READOUT_TIME.to(u.second).value))
            <= (TIME_BLOCK_SIZE.to(u.second).value * (1. - block_use[t]))) 
            for t in slots), "constr_nperslot")

    # program balance.  To avoid key errors, only set constraints 
    # for programs that are present
    requests_needed = []
    for p in requests_allowed.keys():
        if np.sum((dft['program_id'] == p[0]) &
                (dft['subprogram_name'] == p[1])) > 0:
            requests_needed.append(p)

    constr_balance = m.addConstrs(
        ((np.sum(dft.loc[(dft['program_id'] == p[0]) & 
            (dft['subprogram_name'] == p[1]), 'Yrtf'])
        <= requests_allowed[p]) for p in requests_needed), 
        "constr_balance")


    m.update()

    # np.heaviside returns a TypeError so make our own
    def heaviside(x, x0=0):
        # scalars only
        # < and > are not implimented for Gurobi Linexps, so have to do 
        # some unusual control flow here with ==, <=, >=
        if x == 0:
            return x0
        elif x <= 0:
            return 0
        else:
            return 1

    # scale by number of standard exposures so long exposures aren't
    # penalized
    m.setObjective(
        np.sum(dft['Yrtf'] * dft['metric'] * 
        dft['exposure_time']/EXPOSURE_TIME.to(u.second).value) 
        - ydfds.sum() * (FILTER_CHANGE_TIME / (EXPOSURE_TIME +
            READOUT_TIME) * 2.5).value,
#        - np.sum(
#            [heaviside((requests_allowed[p] - np.sum(
#                dft.loc[(dft['program_id'] == p[0]) &
#                (dft['subprogram_name'] == p[1]), 'Yrtf'].values
#                dft['Yrtf'] * 
#                ((dft['program_id'] == p[0]) & (dft['subprogram_name'] == p[1]))
#                )))*2.5 
#                for p in requests_needed]),
        GRB.MAXIMIZE)



    # set a minimum metric value we'll allow, so that flagged limiting mags
    # (-99) are locked out: 1e-5 is limiting mag ~13
    # need to use generalized constraints 

    # this ought to work but gurobi can't seem to parse the sense variable
    # correctly
    #constr_min_metric = m.addConstrs((((row['Yrtf'] == 1) >> (row['metric'] >= 1.e-5)) for (_, row) in dft.iterrows()), "constr_min_metric")
    # so do the slow loop:
#    for idx, row in dft.iterrows():
#        m.addGenConstrIndicator(row['Yrtf'], True, row['metric'], 
#                GRB.GREATER_EQUAL, 1.e-5)

    # sadly above leads to infeasible models


    # Quick and dirty is okay!
    m.Params.TimeLimit = time_limit.to(u.second).value

    m.update()

    m.optimize()

    if (m.Status != GRB.OPTIMAL) and (m.Status != GRB.TIME_LIMIT):
        raise ValueError("Optimization failure")


    # now get the decision variables.  Use > a constant to avoid 
    # numerical precision issues
    dft['Yrtf_val'] = dft['Yrtf'].apply(lambda x: x.getAttr('x') > 0.1) 

    df_schedule = dft.loc[dft['Yrtf_val'],['slot','metric_filter_id', 'request_id']]

#    n_iterations = 1    
    # if we don't optimize long enough, we can end up not satisfying
    # our constraints.  In that case, continue the optimization
#    while df_schedule.groupby(['slot','request_id']).agg(len).max()[0] > 1:
#        n_iterations += 1
#        if n_iterations > 10:
#            raise ValueError('Optimization failed to satisfy constraints')
#        print("> Slot optimization did not satisfy all constraints. Continuing Optimization (Iteration {})".format(n_iterations)) 
#        m.update()
#        m.optimize()

        # now get the decision variables
#        dft['Yrtf_val'] = dft['Yrtf'].apply(lambda x: x.getAttr('x') > 0.1)
#        df_schedule = dft.loc[dft['Yrtf_val'],['slot','metric_filter_id', 'request_id']]

    # get the request set decision variables
    dfr['Yr_val'] = dfr['Yr'].apply(lambda x: x.getAttr('x') > 0.1)

    # this doesn't work in the objective function but is a useful check
    def num_filter_changes(ytf):

        n_changes = 0
        for i, slot in enumerate(slots[:-1]):
            for fid in filter_ids:
                if ytf[(slot,fid)].getAttr('x') == 1:
                    if not (ytf[(slots[i+1], fid)].getAttr('x') == 1):
                        n_changes+=1
        return n_changes

    print(f'Number of filter changes: {num_filter_changes(ytf)}')

    return dfr.loc[dfr['Yr_val'],'program_id'].index, df_schedule, dft

def request_set_optimize(df_metric, df, requests_allowed, 
        time_limit=30*u.second):
    """Identify which request sets to observe tonight.

    Decision variable is yes/no per request_id"""

    request_sets = df_metric.index.values
    slots = np.unique(df_metric.columns.get_level_values(0).values)
    filter_ids = np.unique(df_metric.columns.get_level_values(1).values)

    # can try working with it in 2D/3D, but may be easier just tidy up
    #idx = pd.IndexSlice
    #df_metric.loc[idx[:],idx[:,2]]
    # df_metric.unstack()
    
    # make a copy so I don't have downstream problems
    df_metric_local = df_metric.copy()
    
    df_metric_local['request_id'] = df_metric_local.index
    dft = pd.melt(df_metric_local,id_vars='request_id',
        var_name=['slot','metric_filter_id'],
        value_name='metric')
    # get n_reqs by fid
    n_reqs_cols = ['n_reqs_{}'.format(fid) for fid in filter_ids]
    n_reqs_cols.append('total_requests_tonight')
    dft = pd.merge(dft,df[n_reqs_cols],left_on='request_id',right_index=True)

    # nreqs_{fid} weighted sum over the filters
    for fid in filter_ids:
        wfid = dft['metric_filter_id'] == fid
        n_req_col = 'n_reqs_{}'.format(fid)
        dft.loc[wfid, 'metric'] *= (dft.loc[wfid, n_req_col] / 
            dft.loc[wfid, 'total_requests_tonight'])
    grprs = dft.groupby(['request_id','slot'])
    dfrs = grprs['metric'].agg(np.sum)

    # calculate n_usable slots
    grpr = dfrs.groupby('request_id')
    n_usable = grpr.agg(lambda x: np.sum(x > 0.05)).astype(int)
    n_usable.name = 'n_usable' 
    # also make a df_usable with slot columns for below
    df_usable = dfrs.unstack() > 0.05

    # sum df_metric down to one column
    metric_sum = grpr.agg(lambda x: np.sum(np.where(x > 0, x, 0)))
    metric_sum.name = 'metric_sum'

    # merge additional useful info
    dfr = df[['program_id','subprogram_name','total_requests_tonight']].join(n_usable).join(metric_sum)

    dfr['occupancy'] = dfr['total_requests_tonight']/dfr['n_usable']
    # zero out any unusable slots
    dfr.loc[dfr['n_usable'] == 0, 'occupancy'] = 0.

    # Create an empty model
    m = Model('requests')

    # set the number of threads Gurobi uses
    if 'GRB_USE_NTHREADS' in os.environ:
        m.Params.Threads = int(os.environ['GRB_USE_NTHREADS'])

    # decision variable: yes or no for each request set
    yr_dict = m.addVars(df_metric_local.index,name='Yr',vtype=GRB.BINARY)
    yr_series = pd.Series(yr_dict,name='Yr')
    dfr = dfr.join(yr_series)

    m.setObjective(np.sum(dfr['Yr'] * dfr['metric_sum'] * dfr['occupancy']), 
        GRB.MAXIMIZE)


    # slot occupancy constraint: nreqs obs divided over nusable slots
    constr_avg_slot_occupancy = m.addConstrs(
        ((np.sum(df_usable[t]*dfr['occupancy'] * dfr['Yr'])
        <= max_exps_per_slot) for t in slots), "constr_avg_slot_occupancy")

    # program balance.  To avoid key errors, only set constraints 
    # for programs that are present
    requests_needed = []
    for p in requests_allowed.keys():
        if np.sum((dfr['program_id'] == p[0]) &
                (dfr['subprogram_name'] == p[1])) > 0:
            requests_needed.append(p)

    constr_balance = m.addConstrs(
        ((np.sum(dfr.loc[(dfr['program_id'] == p[0]) & 
                (dfr['subprogram_name'] == p[1]), 'Yr'] * 
            dfr.loc[(dfr['program_id'] == p[0]) & 
                (dfr['subprogram_name'] == p[1]), 'total_requests_tonight'])
        <= requests_allowed[p]) for p in requests_needed), 
        "constr_balance")

    m.Params.TimeLimit = time_limit.to(u.second).value

    m.update()

    m.optimize()

    if (m.Status != GRB.OPTIMAL) and (m.Status != GRB.TIME_LIMIT):
        raise ValueError("Optimization failure")


    # now get the decision variables
    dfr['Yr_val'] = dfr['Yr'].apply(lambda x: x.getAttr('x') > 0.1)

    return dfr.loc[dfr['Yr_val'],'program_id'].index, dft


def slot_optimize(df_metric, df, requests_allowed, time_limit=30*u.second):
    """Determine which slots to place t  he requests in.

    Decision variable is yes/no per request_id, slot, filter,
    with an additional decision variable on which filter to use in which slot"""

    request_sets = df_metric.index.values
    # these are fragile when columns get appended
    slots = np.unique(df_metric.columns.get_level_values(0).values)
    filter_ids = np.unique(df_metric.columns.get_level_values(1).values)
    # extra columns floating around cause problems
    filter_ids = [fid for fid in filter_ids if fid != '']

    # flatten the metric dataframe to make it easier to work with 
    df_metric_local = df_metric.copy()
    df_metric_local['request_id'] = df_metric_local.index

    # make a "tidy" dataframe with one row per (request, slot, filter)
    dft = pd.melt(df_metric_local,id_vars='request_id',
        var_name=['slot','metric_filter_id'],
        value_name='metric')
    # get n_reqs by fid
    n_reqs_cols = ['n_reqs_{}'.format(fid) for fid in filter_ids]
    n_reqs_cols.extend(['program_id','subprogram_name',
        'total_requests_tonight','exposure_time'])
    dft = pd.merge(dft,df[n_reqs_cols],left_on='request_id',right_index=True)

    # Create an empty model
    m = Model('slots')

    # set the number of threads Gurobi uses
    if 'GRB_USE_NTHREADS' in os.environ:
        m.Params.Threads = int(os.environ['GRB_USE_NTHREADS'])

    yrtf_dict = m.addVars(dft.index,name='Yrtf',vtype=GRB.BINARY)
    yrtf_series = pd.Series(yrtf_dict,name='Yrtf')
    dft = dft.join(yrtf_series)


    # no more than nreqs_{fid} slots assigned per request set
    constr_nreqs = m.addConstrs(
        ((np.sum(dft.loc[(dft['request_id'] == r) & 
                        (dft['metric_filter_id'] == f), 'Yrtf']) 
                        <= df.loc[r,'n_reqs_{}'.format(f)])
                        for f in filter_ids for r in request_sets), 
                        "constr_nreqs")

    # create resultant variables: Ytf = 1 if slot t has filter f used
    ytf = m.addVars(slots, filter_ids, vtype=GRB.BINARY)
    for t in slots:
        for f in filter_ids:
            m.addGenConstrOr(ytf[t,f], 
                dft.loc[(dft['slot'] == t) &
                        (dft['metric_filter_id'] == f), 'Yrtf'], #tolist() 
                        "orconstr_{}_{}".format(t,f))

    # now constrain ourselves to one and only one filter per slot.  
    constr_onefilter = m.addConstrs(
        (ytf.sum(t,'*') <= 3 for t in slots), 'constr_onefilter')

    # create filter change resultant variable: Ydfds = 1 if
    # filter changes between slot s and s+1
    ydfds = m.addVars(slots[:-1], vtype=GRB.BINARY)
    # use indicator constraints to set the value
    for i,t in enumerate(slots[:-1]):
        for f in filter_ids:
            m.addGenConstrIndicator(ydfds[t], False,
                ytf[slots[i],f] - ytf[slots[i+1], f], GRB.EQUAL, 0,
                        "filt_change_indicator_{}_{}".format(t,f))
    

    # total exposure time constraint 
    constr_nperslot = m.addConstrs(
        ((np.sum(dft.loc[dft['slot'] == t, 'Yrtf'] * 
            (dft.loc[dft['slot'] == t, 'exposure_time'] + 
                READOUT_TIME.to(u.second).value))
            <= TIME_BLOCK_SIZE.to(u.second).value) 
            for t in slots), "constr_nperslot")

    # program balance.  To avoid key errors, only set constraints 
    # for programs that are present
    requests_needed = []
    for p in requests_allowed.keys():
        if np.sum((dft['program_id'] == p[0]) &
                (dft['subprogram_name'] == p[1])) > 0:
            requests_needed.append(p)

    constr_balance = m.addConstrs(
        ((np.sum(dft.loc[(dft['program_id'] == p[0]) & 
            (dft['subprogram_name'] == p[1]), 'Yrtf'])
        <= requests_allowed[p]) for p in requests_needed), 
        "constr_balance")


    # scale by number of standard exposures so long exposures aren't
    # penalized
    m.setObjective(
        np.sum(dft['Yrtf'] * dft['metric'] * 
        dft['exposure_time']/EXPOSURE_TIME.to(u.second).value) 
        - ydfds.sum() * (FILTER_CHANGE_TIME / (EXPOSURE_TIME +
            READOUT_TIME) * 2.5).value,
        GRB.MAXIMIZE)


    # set a minimum metric value we'll allow, so that flagged limiting mags
    # (-99) are locked out: 1e-5 is limiting mag ~13
    # need to use generalized constraints 

    # this ought to work but gurobi can't seem to parse the sense variable
    # correctly
    #constr_min_metric = m.addConstrs((((row['Yrtf'] == 1) >> (row['metric'] >= 1.e-5)) for (_, row) in dft.iterrows()), "constr_min_metric")
    # so do the slow loop:
#    for idx, row in dft.iterrows():
#        m.addGenConstrIndicator(row['Yrtf'], True, row['metric'], 
#                GRB.GREATER_EQUAL, 1.e-5)

    # sadly above leads to infeasible models


    # Quick and dirty is okay!
    m.Params.TimeLimit = time_limit.to(u.second).value

    m.update()

    m.optimize()

    if (m.Status != GRB.OPTIMAL) and (m.Status != GRB.TIME_LIMIT):
        raise ValueError("Optimization failure")


    # now get the decision variables.  Use > a constant to avoid 
    # numerical precision issues
    dft['Yrtf_val'] = dft['Yrtf'].apply(lambda x: x.getAttr('x') > 0.1) 

    df_schedule = dft.loc[dft['Yrtf_val'],['slot','metric_filter_id', 'request_id']]

#    n_iterations = 1    
    # if we don't optimize long enough, we can end up not satisfying
    # our constraints.  In that case, continue the optimization
#    while df_schedule.groupby(['slot','request_id']).agg(len).max()[0] > 1:
#        n_iterations += 1
#        if n_iterations > 10:
#            1/0
#        print("> Slot optimization did not satisfy all constraints. Continuing Optimization (Iteration {})".format(n_iterations)) 
#        m.update()
#        m.optimize()

        # now get the decision variables
#        dft['Yrtf_val'] = dft['Yrtf'].apply(lambda x: x.getAttr('x') > 0.1)
#        df_schedule = dft.loc[dft['Yrtf_val'],['slot','metric_filter_id', 'request_id']]


    # this doesn't work in the objective function but is a useful check
    def num_filter_changes(ytf):

        n_changes = 0
        for i, slot in enumerate(slots[:-1]):
            for fid in filter_ids:
                if ytf[(slot,fid)].getAttr('x') == 1:
                    if not (ytf[(slots[i+1], fid)].getAttr('x') == 1):
                        n_changes+=1
        return n_changes

    print(f'Number of filter changes: {num_filter_changes(ytf)}')

    return df_schedule

def tsp_optimize(pairwise_distances, time_limit=30*u.second):
    # core algorithmic code from
    # http://examples.gurobi.com/traveling-salesman-problem/

    # Callback - use lazy constraints to eliminate sub-tours 
    def subtourelim(model, where): 
        if where == GRB.callback.MIPSOL: 
            selected = [] 
            # make a list of edges selected in the solution 
            for i in range(n): 
                sol = model.cbGetSolution([model._vars[i,j] for j in range(n)]) 
                selected += [(i,j) for j in range(n) if sol[j] > 0.5] 
            # find the shortest cycle in the selected edge list 
            tour = subtour(selected) 
            if len(tour) < n: 
                # add a subtour elimination constraint 
                expr = 0 
                for i in range(len(tour)): 
                    for j in range(i+1, len(tour)): 
                        expr += model._vars[tour[i], tour[j]] 
                model.cbLazy(expr <= len(tour)-1) 

    # Given a list of edges, finds the shortest subtour 
    def subtour(edges): 
        visited = [False]*n 
        cycles = [] 
        lengths = [] 
        selected = [[] for i in range(n)] 
        for x,y in edges: 
            selected[x].append(y) 
        while True: 
            current = visited.index(False) 
            thiscycle = [current] 
            while True: 
                visited[current] = True 
                neighbors = [x for x in selected[current] if not visited[x]] 
                if len(neighbors) == 0: 
                    break 
                current = neighbors[0] 
                thiscycle.append(current) 
            cycles.append(thiscycle) 
            lengths.append(len(thiscycle)) 
            if sum(lengths) == n: 
                break 
        return cycles[lengths.index(min(lengths))] 

    assert (pairwise_distances.shape[0] == pairwise_distances.shape[1])
    n = pairwise_distances.shape[0]

    # avoid optimization failures if we only feed in a couple of points
    if n == 1:
        return [0], [READOUT_TIME.to(u.second).value]
    if n == 2:
        return [0, 1], [pairwise_distances[0,1]]
    
    m = Model() 

    # set the number of threads Gurobi uses
    if 'GRB_USE_NTHREADS' in os.environ:
        m.Params.Threads = int(os.environ['GRB_USE_NTHREADS'])
        

    # Create variables 
    vars = {} 
    for i in range(n): 
        for j in range(i+1): 
            vars[i,j] = m.addVar(obj=pairwise_distances[i,j], vtype=GRB.BINARY, name='e'+str(i)+'_'+str(j)) 
            vars[j,i] = vars[i,j] 
        m.update() 

    # Add degree-2 constraint, and forbid loops 
    for i in range(n): 
        m.addConstr(quicksum(vars[i,j] for j in range(n)) == 2) 
        vars[i,i].ub = 0 
    
    # W add time limit 
    m.Params.TimeLimit = time_limit.to(u.second).value
    
    m.update()
    # Optimize model 
    m._vars = vars 
    m.params.LazyConstraints = 1 
    m.optimize(subtourelim) 

    if m.Status != GRB.OPTIMAL:
        raise ValueError("Optimization failure")

    solution = m.getAttr('x', vars) 
    selected = [(i,j) for i in range(n) for j in range(n) if solution[i,j] > 0.5] 
    distances = np.sum([pairwise_distances[s] for s in selected])
    distance = m.objVal
    assert len(subtour(selected)) == n

    # dictionary of connected nodes
    edges = defaultdict(list)
    for i in range(n): 
        for j in range(n): 
            if vars[i,j].getAttr('x') > 0.5:
                edges[i].append(j)

    def unwrap_tour(edges, start_node=None):
        if start_node is None:
            start_node = 0
        
        current_node = start_node 
        # arbitrary choice of direction
        next_node = edges[start_node][0]
        tour = [start_node]

        while next_node != start_node:
            tour.append(next_node)
            edge_nodes = edges[next_node]
            assert (current_node in edge_nodes)
            assert(len(edge_nodes) == 2)
            if edge_nodes[0] == current_node:
                tmp = edge_nodes[1]
            elif edge_nodes[1] == current_node:
                tmp = edge_nodes[0]
            current_node = next_node
            next_node = tmp

        return tour
            

    tour = unwrap_tour(edges)
    assert (len(tour) == n)

    return tour, distance
