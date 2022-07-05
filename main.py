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

height_cnt = 0
col_cnt = 0


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

def merge_tabs_to_pdf(songs):

	pdfkit.from_string(merge_tabs_to_html(songs), 'out.pdf' , options = {
    'page-height': str(A4_HEIGHT)+'px',
    'page-width': str(A4_WIDTH)+'px',})
	return



def main():
	download_tab_urls=["https://tabs.ultimate-guitar.com/tab/ed-sheeran/afterglow-chords-3477983", 
	"https://tabs.ultimate-guitar.com/tab/ed-sheeran/i-dont-care-chords-2704800",
	"https://tabs.ultimate-guitar.com/tab/vance-joy/riptide-chords-1237247",
	"https://tabs.ultimate-guitar.com/tab/passenger/let-her-go-chords-1137467",
	"https://tabs.ultimate-guitar.com/tab/coldplay/yellow-chords-114080",
	"https://tabs.ultimate-guitar.com/tab/the-cranberries/zombie-chords-844902",
	"https://tabs.ultimate-guitar.com/tab/elton-john/your-song-chords-29113",
	"https://tabs.ultimate-guitar.com/tab/john-legend/all-of-me-chords-1248578",
	"https://tabs.ultimate-guitar.com/tab/john-legend/all-of-me-chords-1248578",
	"https://tabs.ultimate-guitar.com/tab/johnny-cash/hurt-chords-89849",
	"https://tabs.ultimate-guitar.com/tab/the-beatles/hey-jude-chords-1061739",
	]
	downloaded_songs = []
	for url in download_tab_urls:
		downloaded_songs.append(download_tab(url));

	merge_tabs_to_pdf(downloaded_songs)
	print(merge_tabs_to_html(downloaded_songs))

	return






if __name__ == "__main__":
	main()
