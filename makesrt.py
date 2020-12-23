import json
import re
import string
import datetime
import srt

pattern = re.compile('[\W_]+')

FRAME_DURATION = 1. / 24
SHIFT_LEFT_FRAMES = 10.

with open('asrOutput.json') as f:
    js = json.load(f)

results = js['results']

trans = results['transcripts']

assert len(trans) == 1

the_transcript = trans[0]['transcript']

sentences = [i.strip() for i in the_transcript.split('.') if i.strip()]

def get_item(io):
    item = results['items'][io]
    content = item['alternatives'][0]['content']
    start = item.get('start_time')
    if start is None:
        return None
    end = item['end_time']
    return (float(start), float(end), content)


class SubtitlesBuilder(object):

    def __init__(self):
        self.subtitles = []
        self.io = 0
        self.isen = 0

    def fetch_one(self):
        while True:
            xw = get_item(self.io)
            self.io += 1
            if xw is None:
                continue
            return xw

    def break_sub(self, start, end, sentence):
        self.isen += 1
        # One extra frame left at the end-so they don't overlap with the start
        # of the next
        self.subtitles.append(srt.Subtitle(self.isen,
                                           datetime.timedelta(milliseconds=(1000 * (start - (SHIFT_LEFT_FRAMES * FRAME_DURATION)))),
                                           datetime.timedelta(milliseconds=(1000 * (end - ((SHIFT_LEFT_FRAMES + 1) * FRAME_DURATION)))),
                                           sentence))

    def build(self):
        min_start = None
        max_end = None
        for iz, sentence in enumerate(sentences):
            break_next = False
            buffer = ""
            for word in sentence.split():
                start, end, content = self.fetch_one()

                # * if more than half a second silence, break
                # new line. In this case the old subtitle
                # extends till the new punch i.e. the old
                # max_end gets modified.
                # * If last one had comma, break new line
                # * if more than ? characters, break new line
                if (break_next or
                      (max_end is not None and (start - max_end) > 0.8) or
                      (len(buffer) > 50)):
                    if (start - max_end) > 1.2:
                        last_ends_at = (max_end + 1)
                    else:
                        last_ends_at = start
                    self.break_sub(min_start,
                                   last_ends_at,
                                   buffer)
                    buffer = ""
                    min_start = start
                    max_end = start
                    break_next = False

                if min_start is None or min_start > start:
                    min_start = start

                if max_end is None or max_end < end:
                    max_end = end

                space = ' ' if buffer else ''
                if word.endswith(','):
                    break_next = True
                    buffer += f'{space}{word[:-1]}'
                else:
                    buffer += f'{space}{word}'

            self.break_sub(min_start, max_end, buffer)
            min_start = max_end
            
            # if iz == 5:
            #     break

        return self.subtitles


print(srt.compose(SubtitlesBuilder().build()))
