from datetime import datetime, timedelta
import json

from flask import Flask, request
from pytube import YouTube
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled as TranscriptsException

app = Flask(__name__)


@app.route('/')
def home():
    return "I'm alive"


@app.route('/test')
def test():
    return 'test'


@app.route('/json/en/<path:rest>')
@app.route('/json/ru/<path:rest>')
@app.route('/json/<path:rest>')
def get_json(rest=''):
    video_id = get_video_id(rest)

    if video_id is None:
        return "It's not link for YouTube! Nothing to show."

    rest = f"https://youtu.be/{video_id}"
    data = get_video_meta(rest, video_id)

    return json.dumps(data)


@app.route('/en/<path:rest>')
@app.route('/ru/<path:rest>')
@app.route('/<path:rest>')
def get_subs(rest=''):
    video_id = get_video_id(rest)

    if video_id is None:
        return "It's not link for YouTube! Nothing to show."

    first_lang, second_lang = get_language(request.full_path)

    try:
        data = get_subtitles(video_id, first_lang, second_lang)
    except TranscriptsException:
        data = 'null'
    # except Exception as e:
    #     data = 'null'

    return data


def get_language(path):
    if '/en/' in path:
        return 'en', 'ru'
    else:
        return 'ru', 'en'


def get_video_id(rest):
    if rest.count('youtube.com'):
        return request.args.get('v')
    elif rest.count('youtu.be'):
        video_id = rest.split('/')[-1]

        if video_id[-1] == '?':
            return video_id[:-1]
        else:
            return video_id


def get_video_meta(url, video_id):
    data = YouTube(url)
    data.bypass_age_gate()

    result = {
        'author': data.author,
        'title': data.title,
        'length': data.length,
        'duration': str(timedelta(seconds=data.length)),
        'publish_date': get_str_from_date(data.publish_date),
        'thumbnail_url': data.thumbnail_url,
        'channel_url': data.channel_url,
        'share_url': data.embed_url.replace('www.youtube.com/embed/', 'youtu.be/'),
    }

    if len(data.caption_tracks):
        first_lang, second_lang = get_language(request.full_path)

        result['subtitles'] = get_subtitles(video_id, first_lang, second_lang)
    else:
        result['subtitles'] = 'null'

    return result


def get_str_from_date(date):
    return date.strftime("%d.%m.%Y %H:%M:%S")


def get_subtitles(video_id, first_lang, second_lang):
    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
    data = None

    for transcript in transcript_list:
        if transcript.is_generated:
            continue

        if first_lang in transcript.language_code:
            data = transcript.fetch()

            break
        elif second_lang in transcript.language_code:
            if transcript.is_translatable:
                data = transcript.translate(first_lang).fetch()
            else:
                data = transcript.fetch()
        elif data is None and transcript.is_translatable:
            data = transcript.translate(first_lang).fetch()

    if not data:
        for transcript in transcript_list:
            if second_lang == 'en' and second_lang in transcript.language_code:
                if transcript.is_translatable:
                    data = transcript.translate(first_lang).fetch()
                else:
                    data = transcript.fetch()
                break
            elif first_lang in transcript.language_code:
                data = transcript.fetch()
                break
            elif second_lang == 'ru' and second_lang in transcript.language_code:
                if transcript.is_translatable:
                    data = transcript.translate(first_lang).fetch()
                else:
                    data = transcript.fetch()
                break
            elif data is None and transcript.is_translatable:
                data = transcript.translate(first_lang).fetch()
                # break

    text = ''

    for line in data:
        text += f"\n{line.get('text')}"

    if text == '':
        return 'null'

    return text
