import os
import re
import sys
import json
import requests
import html
#from var_dump import var_dump
from time import sleep
from fpdf import FPDF
import pdfkit
from pyquery import PyQuery as pq

RESULTS_PATTERN_TAB = "\"wiki_tab\":({.*?})"
DATA_CONTENT = "data-content=\"(.*)\""
CHORD_PATTERN = "\[ch\](.*?)\[/ch\]"

A4_HEIGHT = 3508/2.7
A4_WIDTH = 2480/2.7

PTtoMM = 0.3527777778
A4MM_HEIGHT = 297
A4MM_WIDTH = 210

height_cnt = 0
col_cnt = 0

#Global pdf
x_coord = 10.0
y_coord = 10.0
left_column = True
base_font_size = 12


def download_tab_ultimate_guitar(url):
	response = requests.get(url)

	try:
		# isolate results from page using regex
		response_body = html.unescape(response.content.decode())
		results = re.search(DATA_CONTENT, response_body).group(1)
	except AttributeError:
		results = ''
	response_data = json.loads(results)

	songname = response_data.get("store",{}).get("page",{}).get("data",{}).get("tab",{}).get("song_name","")
	artist = response_data.get("store",{}).get("page",{}).get("data",{}).get("tab",{}).get("artist_name","")
	key = response_data.get("store",{}).get("page",{}).get("data",{}).get("tab",{}).get("tonality_name","")
	capo = str(response_data.get("store",{}).get("page",{}).get("data",{}).get("tab_view",{}).get("meta",{}).get("capo","-"))

	content = response_data.get("store",{}).get("page",{}).get("data",{}).get("tab_view",{}).get("wiki_tab",{}).get("content","")
	

	if(len(content) < 100):
		print(songname + " seems bad (shorter than 100 chars)")
		return None
	
	content = content.replace("[tab]","")
	content = content.replace("[/tab]","")

	ret = {
	"songname" : songname,
	"artist"		: artist,
	"key"	: key,
	"capo" : capo,
	"content": content
	}

	return ret

def download_tab_supermusic(url):

	response = requests.get(url)

	try:
		response_body = html.unescape(response.text)
		#results = re.search(DATA_CONTENT, response_body).group(1)
	except AttributeError:
		results = ''
	
	doc = pq(response_body)
	artist = doc(".test3").text().split(' - ')[0]
	songname = doc(".test3").text().split(' - ')[1]

	song = doc(".piesen").html()

	
	new_html = re.sub(r'(<script(.|\n)*?</script>)', '', song)

	
	new_html = re.sub(r'<div.*?>(.*?)<\/div>', '\2', new_html)
	new_html = re.sub(r'<img.*?/>', '', new_html)
	

	new_html = html.unescape(new_html)

	new_html = re.sub(r'<a.*?class=\"sup\".*?>(.+?)</a>',r'[ch]\1[/ch]',new_html)

	new_html = new_html.replace("<sup>","")
	new_html = new_html.replace("</sup>","")

	new_html = new_html.replace("<br/>","")

	lineiterator = iter(new_html.splitlines()[:-2])
	next(lineiterator)
	#remove blank lines from beggining
	beg = True
	content=""
	for line in lineiterator:
		chord_line = ""
		if beg:
			if len(line) < 1:
				continue
			else:
				beg = False
		
		chord_char_cnt = 0
		if line.find('[ch]') != -1:
			chords = re.findall(r'\[ch\].+?\[\/ch\]',line)
			for i in range(line.count('[ch]')):
				chord_line += " " * (line.find("[ch]") - (chord_line.count(' ')))
				line = re.sub(r'(\[ch\].+?\[\/ch\])','',line,1)
				chord_line += chords[i]


		line = ' '+ line	

		if len(chord_line) > 0:
			content += chord_line +"\n" + line +"\n"
		else:
			content += line + "\n"


	ret = {
	"songname" : songname,
	"artist"		: artist,
	"key"	: "?",
	"capo" : "?",
	"content": content
	}

	return ret

def get_song_max_width(pdf,lines):
	i_curr = 12;
	found = False

	while not found:
		found = True
		pdf.set_font_size(i_curr)
		for line in lines:
			line = line.replace("[b]","")
			line = line.replace("[/b]","")
			if(pdf.get_string_width(line) > A4MM_WIDTH/2-20):
				found = False
				if i_curr < 9:
					i_curr -= 0.2
				else:
					i_curr -= 1
				break
	return i_curr




def write_formatted_line(pdf, txt):
	global x_coord,y_coord,left_column,base_font_size

	x_coord = 10 if left_column else (A4MM_WIDTH/2)+5

	i = 0
	br = False
	skip = False
	while i < len(txt):
	
		if txt[i] == '[':
			if txt[i+1] == 'b':
				pdf.set_font('Roboto MonoB')
				skip = True
				i = i+1
			elif txt[i+1] == '/':
				pdf.set_font('Roboto Mono')
				skip = True
				i = i+1
			while txt[i-1]!= ']' and skip:
				i += 1
				if i >= len(txt):
					y_coord += pdf.font_size + 0.2
					return
			skip = False
					
		pdf.text(x_coord,y_coord,txt[i])
		x_coord += pdf.get_string_width(txt[i])

		i += 1
		
	y_coord += pdf.font_size + 0.005*base_font_size
		

	return

def make_title_pdf(pdf,name, author, key, capo):
	global base_font_size
	pdf.set_font_size(base_font_size+3)
	write_formatted_line(pdf,"[b]"+name+"[/b] - "+author)
	pdf.set_font_size(base_font_size+1)
	write_formatted_line(pdf,"Key:"+"[b]"+key+"[/b]"+" Capo:"+"[b]"+capo+"[/b]")

	return

def generate_pdf(songs):
	global x_coord,y_coord,left_column,base_font_size
	x_coord = 10
	y_coord = 10

	pdf = FPDF('P', 'mm', 'A4')
	pdf.add_font('Roboto Mono', '', os.getcwd()+"/fonts/RobotoMono-Regular.ttf", uni = True)
	pdf.add_font('Roboto MonoB', '', os.getcwd()+"/fonts/RobotoMono-Bold.ttf", uni = True)

	pdf.set_font('Roboto Mono', style = '', size = 12)
	pdf.add_page()


	for song in songs:
		
		song["content"]=song["content"].replace("[ch]","[b]")
		song["content"]=song["content"].replace("[/ch]","[/b]")+("\n  \n  ")
		song["content"]=song["content"].replace("][","] [")
		lineiterator = iter(song["content"].splitlines())
		base_font_size = get_song_max_width(pdf,lineiterator)
		make_title_pdf(pdf,song["songname"],song["artist"],song["key"],song["capo"])
		pdf.set_font_size(base_font_size)
		lineiterator = iter(song["content"].splitlines())
		for line in lineiterator:

			if (pdf.font_size + y_coord >= A4MM_HEIGHT-10) or ("[b]" in line and 2*pdf.font_size + y_coord >= A4MM_HEIGHT-10):
				if left_column:
					left_column = False
					y_coord = 10
				else:
					pdf.add_page()
					left_column = True
					y_coord = 10
			write_formatted_line(pdf,line)

		ln_x = 10 if left_column else (A4MM_WIDTH/2)+5
		ln_y = y_coord-pdf.font_size-1
		pdf.line(ln_x,ln_y,ln_x+(A4MM_WIDTH/2)-10,ln_y)

	pdf.output('out.pdf', 'F')

	return


def main():
	"""download_tab_urls=[#"https://tabs.ultimate-guitar.com/tab/ed-sheeran/afterglow-chords-3477983", 
	#"https://tabs.ultimate-guitar.com/tab/ed-sheeran/i-dont-care-chords-2704800",
	#"https://supermusic.cz/skupina.php?action=piesen&idskupiny=0&idpiesne=1030861",
	#"https://supermusic.cz/skupina.php?action=piesen&idskupiny=157&idpiesne=774651",
	"https://supermusic.cz/skupina.php?idpiesne=18371"
	]"""
	download_tab_urls = []
	with open('songslist.txt') as my_file:
	    for line in my_file:
	        download_tab_urls.append(line.replace('\n',''))
	downloaded_songs = []

	for url in download_tab_urls:
		if "ultimate-guitar" in url:
			downloaded_songs.append(download_tab_ultimate_guitar(url))
		elif "supermusic" in url:
			downloaded_songs.append(download_tab_supermusic(url))

	generate_pdf(downloaded_songs)
	#var_dump(downloaded_songs)
	return






if __name__ == "__main__":
	main()
