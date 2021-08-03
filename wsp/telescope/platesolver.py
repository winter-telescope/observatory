import os.path
import platform
import subprocess
import tempfile

"""
Orig Author: Kevin Ivarsen
Modified by Nate Lourie
Updated: NPL 7-26-21
Updated paths to be more platform independent.
Also added options to enable running on unix (eg Mac)

Updated: NPL 7-27-21 made object-oriented

Note: to run on mac, must install mono here: https://www.mono-project.com/download/stable/
Use the Stable Version, not the Visual Studio Version (at least that's what I tested on).
By default the mono build will not be added to the path, so to run it from everywhere,
edit (as root) the path file: /etc/paths, by adding a line at the end with:
    /Library/Frameworks/Mono.framework/Versions/Current/bin
Source: https://stackoverflow.com/a/33003816
"""

class PlateSolver(object):
    def __init__(self, ps3cli_path = 'default', catalog_path = 'default'):
        
        # set up the paths to the catalog and platesolve ps3cli.exe program
        if ps3cli_path.lower() == 'default' or ps3cli_path is None:
            ps3cli_path = self.get_default_client_location()
        
        # Set this to the path where the PlateSolve catalogs are located.
        # The directory specified here should contain "UC4" and "Orca" subdirectories.
        # If this is None, we will try to use the default catalog location
        if catalog_path.lower() == 'default' or catalog_path is None:
            catalog_path = self.get_default_catalog_location()
        
        self._ps3cli_path = ps3cli_path
        self._catalog_path = catalog_path
        
        # set up the paths to the platesolve ps3cli.exe and Kepler catalogs
        self._PS3CLI_EXE = os.path.join(self._ps3cli_path, 'ps3cli.exe')
        self._PS3_CATALOG = os.path.join(self._catalog_path, 'Kepler')
        
        # set up a results dictionary which will hold the astrometry soln
        self.results = {}
        
    def is_linux(self):
        return platform.system() == "Linux"
    
    def is_unix(self):
        return platform.system() == "Darwin"
    
    def get_default_catalog_location(self):
        if self.is_linux() or self.is_unix():
            #return os.path.expanduser("~/Kepler")
            return os.path.join(os.getenv("HOME"),'Kepler')
        else:
            #return os.path.expanduser("~\\Documents\\Kepler")
            return os.path.join(os.getenv("HOME"),'Documents','Kepler')
    
    def get_default_client_location(self):
        return os.path.join(os.getenv("HOME"),'ps3cli')
    
    
    def parse_platesolve_output(self, output_file):
        f = open(output_file)
    
        results = {}
    
        for line in f.readlines():
            line = line.strip()
            if line == "":
                continue
    
            fields = line.split("=")
            if len(fields) != 2:
                continue
            
            keyword, value = fields
    
            results[keyword] = float(value)
        
        return results
        
    
    def platesolve(self, image_filepath, arcsec_per_pixel, stdout_destination = None, output_file_path = 'default', stderr_destination = 'default'):
        
        #stdout_destination = None  # Replace with PIPE if we want to capture the output rather than displaying on the console
        
        self._platesolve_stdout_destination = stdout_destination
        
        if output_file_path.lower() == 'default':
            self._platesolve_output_file_path = os.path.join(tempfile.gettempdir(), "ps3cli_results.txt")
        else:
            self._platesolve_output_file_path = output_file_path
        
        if stderr_destination.lower() == 'default':
            self._platesolve_stderr_destination = subprocess.PIPE
        else:
            self._platesolve_stderr_destination = stderr_destination
        """
        if PS3_CATALOG is None:
            catalog_path = get_default_catalog_location()
        else:
            catalog_path = PS3_CATALOG
        """
        args = [
            self._PS3CLI_EXE,
            image_filepath,
            str(arcsec_per_pixel),
            self._platesolve_output_file_path,
            self._catalog_path
        ]
    
        if self.is_linux() or self.is_unix():
            # Linux systems need to run ps3cli via the mono runtime,
            # so add that to the beginning of the command/argument list
            args.insert(0, "mono")
        print(f'passing to subprocess.Popen: args = {args}')
        process = subprocess.Popen(
                args,
                stdout=self._platesolve_stdout_destination,
                stderr=self._platesolve_stderr_destination
                )
    
        (stdout, stderr) = process.communicate()  # Obtain stdout and stderr output from the wcs tool
        exit_code = process.wait() # Wait for process to complete and obtain the exit code
    
        if exit_code != 0:
            # if it doesn't solve, return false, and pass error to self.err
            err = "Error finding solution.\n" + "Exit code: " + str(exit_code) + "\n" + "Error output: " + stderr.decode('utf-8')
            """
            raise Exception(err)
            """
            self.err = err
            return False
        else:
            self.err = None
            # if it does solve, assign the variables
            platesolve_results = self.parse_platesolve_output(self._platesolve_output_file_path)
            self.results = platesolve_results
            return True
        #return platesolve_results
    
    








