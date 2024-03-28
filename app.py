# -*- coding: utf-8 -*-
import secrets, re, subprocess, os, zipfile
from pytube import YouTube
from pytube.exceptions import AgeRestrictedError
from quart import Quart, websocket, session, redirect, url_for, request, render_template, send_file

app = Quart(__name__)
app.secret_key = secrets.token_hex(16)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024 * 1024 * 1024
youtube_pattern = re.compile(r'(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([\w-]+)')

def add_audio_to_video(video_path, audio_path, output_path):
    cmd = ['ffmpeg', '-i', video_path, '-i', audio_path, '-c:v', 'copy', '-c:a', 'aac', '-strict', 'experimental', '-map', '0:v:0', '-map', '1:a:0', '-shortest', output_path]
    subprocess.run(cmd)

def check_file_existence(file_name):
    if os.path.exists(file_name):
        return True
    else:
        return False

current_dir = os.path.dirname(os.path.abspath(__file__))

zip_file_path = os.path.join(current_dir, 'ffmpeg-master-latest-win64-gpl.zip')
if os.path.exists(zip_file_path):
    extract_to_folder = os.path.join(current_dir, 'FFmpeg')
    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to_folder)
    # 要檢查的 FFmpeg bin 目錄路徑
    ffmpeg_bin_path = os.path.join(current_dir, 'FFmpeg/ffmpeg-master-latest-win64-gpl', 'bin')
    print(ffmpeg_bin_path)
    # 檢查 bin 目錄是否已經在 PATH 中
    if ffmpeg_bin_path not in os.environ['PATH']:
        # 將 bin 目錄路徑新增到 PATH 中
        os.environ['PATH'] += os.pathsep + ffmpeg_bin_path
        print("已新增 'ffmpeg-master-latest-win64-gpl/bin' 到環境變數 PATH 中。")
    else:
        print("'ffmpeg-master-latest-win64-gpl/bin' 已經在環境變數 PATH 中。")

locale = os.environ.get('LC_ALL', 'en_US') # You can change country in this line; e.g. 'en_US', 'zh_TW', 'ja_JP'

directories = ['temp/video', 'temp/audio', 'output']
for directory in directories:
    if not os.path.exists(directory):
        os.makedirs(directory)

@app.route('/', methods=['GET', 'POST'])
async def index():
    if request.method == 'POST':
        form = await request.form
        if 'search' in form:
            YT_URL = form["YoutubeURL"]
            if youtube_pattern.match(YT_URL):
                youtube = YouTube(YT_URL)
                title = youtube.title
                image_url = youtube.thumbnail_url
                if locale.startswith('en_US'):
                    return await render_template('index-english.html', URL=image_url, title=title, image_url=image_url, youtube_url=YT_URL)
                elif locale.startswith('zh_TW'):
                    return await render_template('index-chinese.html', URL=image_url, title=title, image_url=image_url, youtube_url=YT_URL)
                elif locale.startswith('ja_JP'):
                    return await render_template('index-japanese.html', URL=image_url, title=title, image_url=image_url, youtube_url=YT_URL)
                else:
                    return await render_template('index-english.html', URL=image_url, title=title, image_url=image_url, youtube_url=YT_URL)
            else:
                if locale.startswith('en_US'):
                    error = 'Invalid Youtube link'
                    return await render_template('index-english.html', error = error, youtube_url=YT_URL)
                elif locale.startswith('zh_TW'):
                    error = '無效的 Youtube 連結'
                    return await render_template('index-chinese.html', error = error, youtube_url=YT_URL)
                elif locale.startswith('ja_JP'):
                    error = '無効な YouTube リンク'
                    return await render_template('index-japanese.html', error = error, youtube_url=YT_URL)
                else:
                    error = 'Invalid Youtube link'
                    return await render_template('index-english.html', error = error, youtube_url=YT_URL)
        elif 'Download_Video' in form:
            YT_URL = form["youtube_url"]
            get_yt = YouTube(YT_URL)
            yt_video_id = get_yt.video_id
            yt_title = get_yt.title
            yt_title = yt_title.replace('/', '-').replace('\\', '-')
            if check_file_existence(f'output/{yt_video_id} ({yt_title}).mp4') is True:
                return await send_file(f'output/{yt_video_id} ({yt_title}).mp4', as_attachment=True, attachment_filename=f'{yt_title}.mp4')
            else:
                try:
                    video = get_yt.streams.filter(resolution='1080p').first()
                except AgeRestrictedError:
                    if locale.startswith('en_US'):
                        error = 'This video is age restricted and cannot be downloaded'
                        return await render_template('index-english.html', error = error, youtube_url=YT_URL)
                    elif locale.startswith('zh_TW'):
                        error = '這部影片具有年齡限制，無法下載'
                        return await render_template('index-chinese.html', error = error, youtube_url=YT_URL)
                    elif locale.startswith('ja_JP'):
                        error = 'このビデオは年齢制限があるためダウンロードできません'
                        return await render_template('index-japanese.html', error = error, youtube_url=YT_URL)
                    else:
                        error = 'This video is age restricted and cannot be downloaded'
                        return await render_template('index-english.html', error = error, youtube_url=YT_URL)
                audio_stream = get_yt.streams.get_audio_only()
                if video is None:
                    video = get_yt.streams.first()
                video_file_path = video.download(f'temp/video')
                audio_file_path = audio_stream.download(f'temp/audio')
                add_audio_to_video(video_file_path, audio_file_path, f'output/{yt_video_id} ({yt_title}).mp4')
                return await send_file(f'output/{yt_video_id} ({yt_title}).mp4', as_attachment=True, attachment_filename=f'{yt_title}.mp4')
        elif 'Download_Audio' in form:
            YT_URL = form["youtube_url"]
            get_yt = YouTube(YT_URL)
            yt_video_id = get_yt.video_id
            yt_title = get_yt.title
            yt_title = yt_title.replace('/', '-').replace('\\', '-')
            if check_file_existence(f'output/{yt_title}.mp3') is True:
                return await send_file(f'output/{yt_title}.mp3', as_attachment=True, attachment_filename=f'{yt_title}.mp3')
            else:
                audio_stream = get_yt.streams.get_audio_only()
                audio_file_path = audio_stream.download(f'/output')
                return await send_file(audio_file_path, as_attachment=True, attachment_filename=f'{yt_title}.mp3')
    if locale.startswith('en_US'):
        return await render_template('index-english.html')
    elif locale.startswith('zh_TW'):
        return await render_template('index-chinese.html')
    elif locale.startswith('ja_JP'):
        return await render_template('index-japanese.html')
    else:
        return await render_template('index-english.html')

if __name__ == '__main__':
    app.run(debug=True)