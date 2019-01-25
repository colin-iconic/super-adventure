import pdfquery
import os
import time
import sys
import pickle
import json
import ctypes
from pprint import pprint
from datetime import datetime
from shutil import copyfile

clear = lambda: os.system('cls')
clear()

before = dict([(f, None) for f in next(os.walk('.'))[1]])

homedir = r'/nas/Production/Laser NC Codes/Nest Checker'
#homedir = r'C:\Users\mcolin\Desktop\Nest Checker'
tasksdir = r'/nas/Production/Laser NC Codes/LP/(0000) MetaCAM Report'
#tasksdir = r'C:\Users\mcolin\Desktop\Nest Checker\Reports'

while True:
	try:
		print('Begin scanning at:\n' + time.ctime())
		os.chdir(homedir)
		copyfile(homedir + r'/data.js', homedir + r'/temp_data.js')
		os.chdir(tasksdir)
		after = dict([(f, None) for f in next(os.walk('.'))[1]])

		for task in sorted(after.keys(), reverse=True):
			if task in ['Archive', 'NCR'] or task.startswith('New folder'):
				print('Skipping...' + task)
				continue
			print('Scanning ' + task +'...')
			jobnums = task.split(',')
			jobnumbers = []
			for each in jobnums:
				try:
					jobnumbers.append(int(each))
				except ValueError:
	#				print('Could not process folder: ' + task + '\n Please rename with job numbers.')
					continue

			os.chdir(tasksdir+'\\'+task)

			report = []

			filelist = os.listdir(tasksdir+'\\'+task)
			flist = []
			dfiles = []
			duplicates = []
			for each in filelist:
				if not each.endswith(".pdf"):
					pass
				elif os.path.basename(each)[-5:-4].isalpha():
					flist.append([each, os.path.basename(each)[14:-5]])
				else:
					flist.append([each, os.path.basename(each)[14:-4]])

			duplicates = []

			for i, x in enumerate(flist):
				for a in flist:
					if x[1] == a[1] and x[0] != a[0]:
						duplicates.append([x, a])
						if x in flist:
							flist.remove(x)
						if a in flist:
							flist.remove(a)

			if not os.path.isdir(tasksdir+'\\'+task+'\\Archive'):
				os.makedirs(tasksdir+'\\'+task+'\\Archive')

			for each in duplicates:
				each = sorted(each, key=lambda x: x[0])
				for i in range(len(each)-1):
					os.rename(each[i][0], tasksdir+'\\'+task+'\\Archive\\'+each[i][0])

			#changing from log folder edit time
			mtime = os.path.getmtime(tasksdir+'\\'+task)
			now = time.time()
			age = (now - mtime)/60
			if age < 30:
				for file in os.listdir(tasksdir+'\\'+task):
					if file.endswith(".pdf"):
						report.append(file)

			layouts = []
			#open nesting results
			tasks = {}
			for fname in report:
				pprint(fname)
				try:
					#load pdf
					pdf = pdfquery.PDFQuery(tasksdir+ '\\'+ task + '\\' + fname)
					pdf.load(None)
				except PDFSyntaxError:
					print(fname + ' is not a valid pdf. Please check file for errors.')
					continue
				except:
					print('Error. No file entered, or file not found.\nCheck %s.') % (fname)
					input("Press Enter to continue...")
					sys.exit(0)

				currentpage = 0
				pagecount = pdf.doc.catalog['Pages'].resolve()['Count']
				while currentpage < pagecount:
					parts = []
					try:
						pdf.load(currentpage)
					except:
						print('could not load page')
						break

					#skip nesting reports
					nesting = pdf.pq('LTTextLineHorizontal:contains("Nesting")')
					if nesting:
						break


					#for each layout report
					programname = pdf.pq('LTTextLineHorizontal:in_bbox("300, 500, 800, 530")').text()[29:-3]
					taskname = pdf.pq('LTTextLineHorizontal:in_bbox("15, 500, 255, 530")').text()[33:-4]

					if not (programname and taskname):
						if not (programname or taskname):
							print('No program or task name: ' + task + '\\' + fname)
							currentpage += 1
							continue

						if not programname:
							programname = taskname

						if not taskname:
							try:
								taskname = programname.split('-')[-2]
							except IndexError:
								taskname = programname

					created = pdf.pq('LTTextLineHorizontal:contains("Date:")').text()[5:]
					copies = pdf.pq('LTTextLineHorizontal:in_bbox("153, 485, 183, 510")').text()
					if copies == '':
						print('No copies, no parts?')
						copies = 0
					copies = int(copies)
					material = pdf.pq('LTTextLineHorizontal:in_bbox("110, 250, 200, 275")').text()
					if material == '':
						print('No material, no parts?')
						break
					thickness = pdf.pq('LTTextLineHorizontal:in_bbox("110, 230, 200, 255")').text()
					thickness = float(thickness)
					length = pdf.pq('LTTextLineHorizontal:in_bbox("200, 250, 340, 275")').text()[18:]
					length = float(length)
					height = pdf.pq('LTTextLineHorizontal:in_bbox("200, 225, 340, 250")').text()[18:]
					height = float(height)
					cutlength = pdf.pq('LTTextLineHorizontal:in_bbox("490, 250, 565, 275")').text()
					try:
						cutlength = float(cutlength)
					except:
						print('No cut length, no parts?')
						break
					pierces = pdf.pq('LTTextLineHorizontal:in_bbox("490, 230, 535, 255")').text()
					try:
						pierces = float(pierces)
					except:
						print('No pierces, no parts?')
						break

					#get part name and qty in sheet
					lineposition = 190
					name = pdf.pq('LTTextLineHorizontal:in_bbox("70, %s, 315, %s")' %(lineposition, lineposition + 30)).text()

					while name is not '':
						quantity = pdf.pq('LTTextLineHorizontal:in_bbox("360, %s, 425, %s")' %(lineposition, lineposition + 30)).text()
						quantity = int(quantity) * copies
						parts.append({'name': name, 'quantity': quantity})
						lineposition -= 13.32
						name = pdf.pq('LTTextLineHorizontal:in_bbox("70, %s, 315, %s")' %(lineposition, lineposition + 30)).text()

					program = {
						"name": programname,
						"filename": fname,
						"date": created,
						"copies": copies,
						"material": material,
						"thickness": thickness,
						"size": [length, height],
						"cutlength": cutlength,
						"pierces": pierces,
						"parts": parts
					}

					nextpage = currentpage + 1
					#check if 2nd page of a layout
					if nextpage < pagecount:
						try:
							pdf.load(nextpage)
						except Exception as exception:
							print('Page load failed.', exception)
							input("Press Enter to continue...")

						plocation = pdf.pq('LTTextLineHorizontal:contains("Part No")')
						try:
							plocation = float(plocation.attr('y0'))

						except ValueError:
							print('Could not find "Part No"')
							input("Press Enter to continue...")

						if plocation is not '' and plocation > 250:
							lineposition = 505
							name = pdf.pq('LTTextLineHorizontal:in_bbox("70, %s, 315, %s")' %(lineposition, lineposition + 30)).text()

							while name is not '':
								quantity = pdf.pq('LTTextLineHorizontal:in_bbox("360, %s, 400, %s")' %(lineposition, lineposition + 30)).text()
								quantity = int(quantity) * copies
								parts.append({'name': name, 'quantity': quantity})
								lineposition -= 13.32
								name = pdf.pq('LTTextLineHorizontal:in_bbox("70, %s, 315, %s")' %(lineposition, lineposition + 30)).text()
							currentpage += 1

					for part in parts:
						part['material'] = material
						part['thickness'] = thickness


					if not taskname in tasks:
						tasks[taskname] = {'jobnumbers': jobnumbers, 'layouts': [program]}
						tasks[taskname]['parts'] = parts
						tasks[taskname]['sheets'] = [{'size': program['size'], 'material': program['material'], 'thickness': program['thickness'], 'quantity': program['copies']}]
					else:
						tasks[taskname]['layouts'].append(program)
						partlist = []
						for each in parts:
							partlist.append(each['name'])

						parttot = []
						for each in tasks[taskname]['parts']:
							parttot.append(each['name'])

						partadd = set(partlist).intersection(parttot)
						for i, e in enumerate(parts):
							if e['name'] in partadd:
								eindex = next(index for (index, d) in enumerate(tasks[taskname]['parts']) if d['name'] == e['name'])
								tasks[taskname]['parts'][eindex]['quantity'] = tasks[taskname]['parts'][eindex]['quantity'] + parts[i]['quantity']
							else:
								tasks[taskname]['parts'].append(e)
						c = 0
						for each in tasks[taskname]['sheets']:
							if each == {'size': program['size'], 'material': program['material'], 'thickness': program['thickness'], 'quantity': each['quantity']}:
								each['quantity'] += program['copies']
								continue
							else:
								c += 1

						if c == len(tasks[taskname]['sheets']):
							tasks[taskname]['sheets'].append({'size': program['size'], 'material': program['material'], 'thickness': program['thickness'], 'quantity': program['copies']})

					print(task + ': ' + fname + ' page ' + str(currentpage) + ' processed.')
					currentpage += 1
				pdf.file.close()
			data = {}
			if os.path.isfile(homedir + r'\data.pickle'):
				with open(homedir + r'\data.pickle', 'rb') as pfile:
					try:
						data = pickle.load(pfile)

					except EOFError:
						print('no pickle')
						data = {}

					except Exception as exception:
						print(Exception)
						data = {}
						pass

			data.update(tasks)

			with open(homedir + r'\data.pickle', 'wb') as data_file:
				pickle.dump(data, data_file, protocol=pickle.HIGHEST_PROTOCOL)

			with open(homedir + r'\temp_data.js', 'w') as jfile:
				jfile.write('var data = ')
				json.dump(data, jfile)
		os.chdir(homedir)
		copyfile(r'temp_data.js', r'data.js')
		os.remove(r'temp_data.js')
		print('Finished scanning at:\n' + time.ctime() + '\n')
	#	input('Press Enter to continue...')
	#	time.sleep(300)
	except Exception as exception:
		print(exception)
		input("Press Enter to continue...")
