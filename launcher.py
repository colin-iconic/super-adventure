from subprocess import Popen
import psutil

def verification():
    for pid in psutil.pids():
        p = psutil.Process(pid)
        if p.name() == "python.exe" and len(p.cmdline()) > 1 and "Nest Checker.py" in p.cmdline()[1]:
            return True
			
while True:
	if not verification():
		print(80*'#'+'\n'+'### STARTING SCRIPT...'+55*' '+'###\n'+80*'#'+'\n')
		p = Popen(r"C:\Users\mcolin\Desktop\Nest Checker\Nest Checker.bat")
		stdout, stderr = p.communicate()
		input("Press Enter to continue...")