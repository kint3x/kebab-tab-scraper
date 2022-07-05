import os
import re
import sys
import json
import requests
import html
from var_dump import var_dump
from time import sleep
from fpdf import FPDF
import pdfkit


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


def download_tab(url):
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
	capo = str(response_data.get("store",{}).get("page",{}).get("data",{}).get("tab_view",{}).get("meta",{}).get("capo","0"))

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

def start_end_check_space(px, text = False):
	global height_cnt,col_cnt
	if((height_cnt+px+40 > A4_HEIGHT) and not text):
		height_cnt_o = height_cnt
		height_cnt = px
		col_cnt += 1
		if(col_cnt % 2 == 1):
			spacer = "<div class='spacer'></div>"
		else:
			spacer = ""
		return "</div>{}<div class='col'>".format(spacer)
	else:
		height_cnt += px
		return ""


def merge_tabs_to_html(songs):
	global height_cnt,col_cnt
	html_inner = "<!DOCTYPE html><html><head>"
	html_inner += "<style> @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;500&display=swap');	\
	*{font-size: 13px; font-family: 'Roboto Mono', monospace;} \
	.title {font-size:17px;} .title .song{font-weight:bold; font-size: 17px;}	\
	ch{ font-weight:bold; background-color:#dddddd;}\
	.line{ min-height:13px;}\
	.col{ width:"+str(round((A4_WIDTH/2)-10,0))+"px;overflow:hidden;} \
	body{ margin-left:30px; width:" + str(A4_WIDTH+30)+"px; display: flex; flex-wrap:wrap; justify-content:space-between;} \
	.spacer{ width:100%; height:2px; }\
	</style></head><body>\
	<div class='col'>"
	
	height_cnt = 0
	col_cnt = 1
	song_idx = 1
	for song in songs:
		line_cnt = 0
		song["content"] = song["content"].replace("[ch]","<ch>")
		song["content"] = song["content"].replace("[/ch]","</ch>")

		if(song_idx != 1):
			margin = "</br>"
		else:
			margin = ""

		html_inner += start_end_check_space(15*2+22)
		html_inner += "{}<div class='title'><span class='song song-{}'>{}</span> - {}</div>".format(margin,song_idx,song["songname"],song["artist"])
		html_inner += "<div class='songinfo'><b>Key:</b> {} <b>Capo:</b>{}</div>".format(song["key"],song["capo"]) 

		lineiterator = iter(song["content"].splitlines())
		for line in lineiterator:
			line_cnt += 1;

			if "<ch>" not in line:
				add_class = "text"
				html_inner += start_end_check_space(16,True)
			else:
				add_class = "chords"
				html_inner += start_end_check_space(16)
			if(add_class == "text"):
				line = line.strip()

			
			html_inner += "<div class='line {}'>{}</div>".format(add_class,line.replace(" ","&nbsp;"))

		song_idx += 1

	html_inner += "</div></body></html>"


	return html_inner

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
	pdf.set_font_size(base_font_size+2)
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
		ln_y = y_coord-pdf.font_size-0.5
		pdf.line(ln_x,ln_y,ln_x+(A4MM_WIDTH/2)-10,ln_y)

	pdf.output('out.pdf', 'F')

	return


def main():
	download_tab_urls=["https://tabs.ultimate-guitar.com/tab/ed-sheeran/afterglow-chords-3477983", 
	"https://tabs.ultimate-guitar.com/tab/ed-sheeran/i-dont-care-chords-2704800",
	]
	downloaded_songs = []
	for url in download_tab_urls:
		downloaded_songs.append(download_tab(url));

	generate_pdf(downloaded_songs)
	#var_dump(downloaded_songs)
	return






if __name__ == "__main__":
	main()
