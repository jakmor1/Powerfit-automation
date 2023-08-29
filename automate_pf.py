import os
import sys
import getopt
import multiprocessing
import re
import pandas as pd
import time
import subprocess

def read_sol_file(location,filename):

    local_dct = {}

    if not os.path.exists(location):
        local_dct[re.sub( "\..*$", "", filename) + "_fit_" + str("error") ] = -1
        return local_dct
        
    f = open(location)

    f.readline()
       

    max_cc = 0
    for i in range(3):       #read first 3 lines and take the solutions with the highest score
        try:       #when there are less than 3 solutions in solutions file break this loop
            current_cc = float(f.readline().split()[1])
            if current_cc < 0 or current_cc > 1: 
                local_dct[re.sub( "\..*$", "", filename) + "_fit_" + str("error") ] = -1
                return local_dct
        except IndexError:
            current_cc = 0
            break
        if(len(local_dct) == 0 or current_cc >= max_cc ):  #take the highest cc values of file
            local_dct[re.sub( "\..*$", "", filename) + "_fit_" + str(i+1) ] = current_cc
            max_cc = current_cc

    f.close()
    return local_dct



def check(): #kill process if exists Zero-filled mask error
    filenames = next(os.walk(os.getcwd()))[2]
    filenames = [fil_nam for fil_nam in filenames if (not fil_nam.startswith(".")) and ".txt" in fil_nam]
    for fil_nam in filenames:
        f = open(fil_nam,"r+")
        all_text = f.read()
        if ("Zero-filled" in all_text)  and (not "checked" in all_text):
            
            fil_nam = fil_nam[6:]
            fil_nam = re.sub( "\..*$", "", fil_nam)
            os.system("pkill -f " + fil_nam)
            f.write("\nchecked")
        elif ("unrecognized arguments:" in all_text):
            print(all_text)
            sys.exit()
        f.close()
           
   
def worker_main(queue):
    while True:
        time.sleep(4)
        check()
        time.sleep(4)
        item = queue.get(block=True)  # block=True means make a blocking call to wait for items in queue
        if item is None:
            break

        item_in_tab = item.split()
        pdb_fil = item_in_tab[3]
        pdb_fil = pdb_fil.split("/")
        pdb_fil = pdb_fil[len(pdb_fil)-1]
        pdb_fil = re.sub( "\..*$", "", pdb_fil)
        
        
        try: #Save stderr to file from current subprocess
            with open("stderr"+ pdb_fil +".txt","wb") as err:
                subprocess.run(item_in_tab,stderr=err)
                
        except Exception as r:
            print(r)

        time.sleep(2)

class powerfit_data:
	map_name = ""
	pdb_loc = os.getcwd()
	map_res = ""
	settings = "-a 10 -p 1 -n 6" #default setings for powerfit
	

def help():
	print("""Required arguments: 
	\n-m \tPath to the map from current location including map name.
	\n-r \tResolution of the map in angstrom
	\n-l \tPath to the location of atomic models to be fitted in the density from current location\n
	\nOptional arguments:
	\n-s \tAdvanced settings of powerfit. To change default settings("a 10 -p 1 -n 6") pass them as string. 
	For example: -s "-a 15 -n 9"
	To see advanced settings of powerfit type "powerfit -h"
	""")

def input():

	powerfit_class = powerfit_data
	argv = sys.argv[1:]

	try:
		opts, args = getopt.getopt(argv, "m:r:l:s:h")

	except getopt.GetoptError as err:
		print(err)
		print("Type -h for help")
		sys.exit()

	for opt, arg in opts:
		if opt in ['-m']:
			powerfit_class.map_name = arg
		elif opt in ['-r']:
			powerfit_class.map_res = arg
		elif opt in ['-l']:
			powerfit_class.pdb_loc = arg
		elif opt in ['-s']:
			powerfit_class.settings = arg
			#print(arg)
		elif opt in ['-h']:
			help()
			sys.exit()
		else:
			print("Unhandled option: {}, -h = help",opt)
			sys.exit()

	return powerfit_class


def main():
	p_number = multiprocessing.cpu_count() -1
	
	start_time = time.time()
	
	powerfit_class = input()
	
	if(powerfit_class.map_res == ""):
		print("Map resolution is mandatory")
		sys.exit()

	try:  #get filenames of atomic models
		filenames = next(os.walk(powerfit_class.pdb_loc))[2]
	except StopIteration:
		print("No files in current location: " + powerfit_class.pdb_loc)
		print("If you want enter path from current location use . \nFor example: ./dir")
		return
	
	if not os.path.isfile(powerfit_class.map_name):  #check map file
		print("File doesn't exist: " + powerfit_class.map_name)
		print("If you want enter path from current location use . \nFor example: ./dir/file")
		return

	# Delete extensions and sort
	filenames = [fil_nam for fil_nam in filenames if (not fil_nam.startswith(".")) and ".pdb" in fil_nam]	
	filenames.sort()

	if len(filenames) == 0:
		print("There is no pdb files in current location: " + powerfit_class.pdb_loc)
		return


	if(os.path.isdir("/tmp/powerfit")): #create tmp dir for powerfit files
		os.system("rm -r /tmp/powerfit")
		os.system("mkdir /tmp/powerfit")
	else:
		os.system("mkdir /tmp/powerfit")


	for fil_nam in filenames:
		cmd = "mkdir /tmp/powerfit/"
		os.system(cmd + re.sub( "\..*$", "", fil_nam))  #remove extension from string
	
		
	#pool of processes
	NUM_QUEUE_ITEMS = len(filenames)
	NUM_PROCESSES = p_number
		
	the_queue = multiprocessing.Queue()
	the_pool = multiprocessing.Pool(NUM_PROCESSES, worker_main, (the_queue,))

	for fil_nam in filenames:
		location ="-d /tmp/powerfit/" + re.sub( "\..*$", "", fil_nam) 
		
		napis = "powerfit " + powerfit_class.map_name + " " + powerfit_class.map_res + " " +powerfit_class.pdb_loc + "/" + fil_nam + " " + powerfit_class.settings + " " + location
		the_queue.put(napis)


	for i in range(NUM_PROCESSES):
		the_queue.put(None)

        # prevent adding anything more to the queue and wait for queue to empty
	the_queue.close()
	the_queue.join_thread()

        # prevent adding anything more to the process pool and wait for all processes to finish
	the_pool.close()
	the_pool.join()
	
	
	os.system("rm stderr*")

     
	

	dct = {}
	for fil_nam in filenames:  #for all solutions.out files
		location ="/tmp/powerfit/" + re.sub( "\..*$", "", fil_nam) + "/solutions.out"
		local_dct = read_sol_file(location, fil_nam)
		for i in local_dct:  #add the highest ccc values of file
			dct[i] = local_dct[i]

	df = pd.DataFrame()  #transform dict to dataframe

	

	df["names"] = dct.keys()
	df["ccc"] = dct.values()
	


	df = df.sort_values("ccc", ascending=False)  #sort dataframe by cc in descending order
	df["no"] = range(1,len(dct)+1)
	df = df[["no","names","ccc"]]
	
	
	map_name = powerfit_class.map_name.split("/")
	map_name = map_name[len(map_name)-1]
	df2 = {'Map name': [map_name],
            'Map resolution': [powerfit_class.map_res],
            'Powerfit settings': [powerfit_class.settings],
            'Number of models': [len(filenames)]}
            
	df2 = pd.DataFrame(df2)


	
	if(os.path.isdir("results")):  
		os.system("rm -r results")

	os.system("mkdir results")

	with pd.ExcelWriter('results/result.xlsx') as writer: #save dataframes to excel
		df.to_excel(writer, sheet_name='Sheet_name_1',index = False)
		df2.to_excel(writer, sheet_name='Sheet_name_1',index = False,startcol = 4)
	
	directories_tmp = next(os.walk("/tmp/powerfit"))[1]

	
	for directory in directories_tmp: #copy fit_files from tmp/powerfit if only they meet condition: fit_file has the biggest cc score in his solution.out file
		fil_in_dir = next(os.walk("/tmp/powerfit/" + directory))[2] 
		fil_in_dir = [file_nam for file_nam in fil_in_dir if ".pdb" in file_nam]
		for fil_nam in fil_in_dir:
			if((directory + "_" + re.sub( "\..*$", "", fil_nam)) in dct):

				os.system("cp /tmp/powerfit/" + directory + "/" + fil_nam + " results/" + directory + "_" + fil_nam)

	print("--- %s seconds ---" % (time.time() - start_time))

if __name__ == "__main__":
	main()


