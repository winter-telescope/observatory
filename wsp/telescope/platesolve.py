import os.path
import platform
from subprocess import Popen, PIPE
import tempfile

"""
Author: Kevin Ivarsen
Updated: 7-26-21 Nate Lourie
Updated paths to be more platform independent.
Also added options to enable running on unix (eg Mac)

Note: to run on mac, must install mono here: https://www.mono-project.com/download/stable/
Use the Stable Version, not the Visual Studio Version (at least that's what I tested on).
By default the mono build will not be added to the path, so to run it from everywhere,
edit (as root) the path file: /etc/paths, by adding a line at the end with:
    /Library/Frameworks/Mono.framework/Versions/Current/bin
Source: https://stackoverflow.com/a/33003816
"""



# Point this to the location of the "ps3cli.exe" executable
#PS3CLI_EXE = os.path.expanduser("~/ps3cli/ps3cli.exe")
PS3CLI_EXE = os.path.join(os.getenv("HOME"),'ps3cli','ps3cli.exe')
# For testing purposes...
#PS3CLI_EXE = r"C:\Users\kmi\Desktop\Planewave work\Code\PWGit\PWCode\ps3cli\bin\Debug\ps3cli.exe"


# Set this to the path where the PlateSolve catalogs are located.
# The directory specified here should contain "UC4" and "Orca" subdirectories.
# If this is None, we will try to use the default catalog location
PS3_CATALOG = None

def is_linux():
    return platform.system() == "Linux"

def is_unix():
    return platform.system() == "Darwin"

def get_default_catalog_location():
    if is_linux() or is_unix():
        #return os.path.expanduser("~/Kepler")
        return os.path.join(os.getenv("HOME"),'Kepler')
    else:
        #return os.path.expanduser("~\\Documents\\Kepler")
        return os.path.join(os.getenv("HOME"),'Documents','Kepler')

def platesolve(image_file, arcsec_per_pixel):
    stdout_destination = None  # Replace with PIPE if we want to capture the output rather than displaying on the console

    output_file_path = os.path.join(tempfile.gettempdir(), "ps3cli_results.txt")

    if PS3_CATALOG is None:
        catalog_path = get_default_catalog_location()
    else:
        catalog_path = PS3_CATALOG

    args = [
        PS3CLI_EXE,
        image_file,
        str(arcsec_per_pixel),
        output_file_path,
        catalog_path
    ]

    if is_linux() or is_unix():
        # Linux systems need to run ps3cli via the mono runtime,
        # so add that to the beginning of the command/argument list
        args.insert(0, "mono")
    print(f'passing to subprocess.Popen: args = {args}')
    process = Popen(
            args,
            stdout=stdout_destination,
            stderr=PIPE
            )

    (stdout, stderr) = process.communicate()  # Obtain stdout and stderr output from the wcs tool
    exit_code = process.wait() # Wait for process to complete and obtain the exit code

    if exit_code != 0:
        raise Exception("Error finding solution.\n" +
                        "Exit code: " + str(exit_code) + "\n" + 
                        "Error output: " + stderr.decode('utf-8'))
    
    return parse_platesolve_output(output_file_path)

def parse_platesolve_output(output_file):
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