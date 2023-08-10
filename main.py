import dataclasses
import enum
import re
import typing

import requests
from bs4 import BeautifulSoup
from googletrans import Translator
from textblob import TextBlob
import matplotlib.pyplot as plt

EXCLUDE_PATTERN = '/search/'
INCLUDE_PATTERN = '/discussion/'

barbie_film_url = 'https://www.filmweb.pl/film/Barbie-2023-754800'
oppenheimer_film_url = 'https://www.filmweb.pl/film/Oppenheimer-2023-10002817'


class Sentiment(enum.Enum):
    Negative = -1
    Neutral = 0
    Positive = 1


@dataclasses.dataclass
class SentimentData:
    negative: int
    neutral: int
    positive: int


def get_all_comments_urls(film_urls: typing.List[str]) -> typing.List[str]:
    comments_urls = []
    for film in film_urls:
        for page_index in range(1, 10):
            main_page_response = requests.get(f'{film}/discussion?plusMinus=true&page={page_index}')
            split_content = str(main_page_response.content).split(sep=" ")
            comments_urls_to_clean = [x for x in split_content if INCLUDE_PATTERN in x]
            comments_urls += comments_urls_to_clean

    return clean_urls(comments_urls)


def clean_urls(data: typing.List[str]) -> typing.List[str]:
    cleaned_urls = []
    barbie_film_split = barbie_film_url.split('pl/')[1].split('/')[1]
    oppenheimer_film_split = oppenheimer_film_url.split('pl/')[1].split('/')[1]
    exclude = [barbie_film_split, oppenheimer_film_split, 'film', 'href']
    first_cleaned = [x for x in data if EXCLUDE_PATTERN not in x]

    for row in first_cleaned:
        row_split = row.split('/')
        second_cleaned = [x for x in row_split if x not in exclude]
        cleaned_urls += second_cleaned

    third_cleaned = [x for x in cleaned_urls if ',' in x]
    removed_duplications = []
    for row in third_cleaned:
        row_split = row.split(',')
        number = re.sub("[^0-9]", "", row_split[1])
        removed_duplications.append(f'{row_split[0]},{number}')

    cleaned_urls = list(set(removed_duplications))

    return cleaned_urls


def get_comments_from_url_list_file(file_path_urls: str, file_path_comments: str):
    comments = []
    with open(file_path_urls) as f:
        lines = f.readlines()
        for line in lines:
            url = f'{barbie_film_url}/discussion/{line}'.strip()

            response = requests.get(url)
            html = response.text
            root = BeautifulSoup(html, features="html.parser")
            for comment_block in root.find_all('p', {'class': 'forumTopicSection__topicText'}):
                comments.append(comment_block.text)

    file = open(file_path_comments, 'w', encoding="utf-8")
    for comment in comments:
        file.write(comment + '\n')
    file.close()


def translate_pl_to_en(txt: str):
    translator = Translator()
    return translator.translate(txt, src='pl', dest='en')


def translate_file(file_path: str, dest_file_path: str):
    translated_comments = []
    with open(file_path, 'r', encoding="utf-8") as f:
        lines = f.readlines()
        for line in lines:
            translated_line = translate_pl_to_en(line).text
            translated_comments.append(translated_line)

    file = open(dest_file_path, 'w', encoding="utf-8")
    for comment in translated_comments:
        file.write(comment + '\n')
    file.close()


def get_sentiment(txt: str) -> Sentiment:
    blob_obj = TextBlob(txt)
    if blob_obj.polarity > 0:
        return Sentiment.Positive
    elif blob_obj.polarity < 0:
        return Sentiment.Negative
    else:
        return Sentiment.Neutral


def sentiment_analysis_for_file(file_path: str) -> SentimentData:
    sentiment_list = []
    with open(file_path, 'r', encoding="utf-8") as f:
        lines = f.readlines()
        for line in lines:
            sentiment = get_sentiment(line.strip())
            sentiment_list.append(sentiment)
    negative_count = sentiment_list.count(Sentiment.Negative)
    neutral_count = sentiment_list.count(Sentiment.Neutral)
    positive_count = sentiment_list.count(Sentiment.Positive)
    return SentimentData(negative_count, neutral_count, positive_count)


if __name__ == '__main__':
    # STEP 1.Get all comments sub-url for specified film

    films = [
        barbie_film_url,
        oppenheimer_film_url
    ]

    comment_url_list = get_all_comments_urls(films)
    for comment_url in comment_url_list:
        print(comment_url)

    # STEP 2. Get comment text value

    files_urls = [
        'static/comments_barbie_titles.txt',
        'static/comments_oppenheimer_titles.txt'
    ]

    file_comments_pl = [
        'static/comments_barbie_PL.txt',
        'static/comments_oppenheimer_PL.txt'
    ]

    get_comments_from_url_list_file(files_urls[0], file_comments_pl[0])
    get_comments_from_url_list_file(files_urls[1], file_comments_pl[1])

    # STEP 3. Translate comments PL - ENG

    file_comments_en = [
        'static/comments_barbie_EN.txt',
        'static/comments_oppenheimer_EN.txt'
    ]

    translate_file(file_comments_pl[0], file_comments_en[0])
    translate_file(file_comments_pl[1], file_comments_en[1])

    # STEP 4. Get sentiment analysis from comments

    for file in file_comments_en:
        sentiment_result = sentiment_analysis_for_file(file)

        fig, ax = plt.subplots()
        ax.pie([sentiment_result.neutral, sentiment_result.negative, sentiment_result.positive],
               labels=[Sentiment.Neutral.name, Sentiment.Negative.name, Sentiment.Positive.name],
               autopct='%1.1f%%')
        plt.title(file, loc="left")
        plt.savefig(f"{file.replace('.txt', '')}.png")


