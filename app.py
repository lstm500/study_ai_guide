import base64
import html
import os
import re
from html.parser import HTMLParser
from urllib.request import Request, urlopen
from urllib.parse import urljoin, urlparse

import streamlit as st

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

try:
    from youtube_transcript_api import YouTubeTranscriptApi
except Exception:
    YouTubeTranscriptApi = None


st.set_page_config(
    page_title="さんすうナビ",
    page_icon="🧮",
    layout="wide",
    initial_sidebar_state="collapsed",
)

MEXT_URL = "https://www.mext.go.jp/a_menu/shotou/new-cs/1387014.htm"
MEXT_MATH_PDF = "https://www.mext.go.jp/content/20211102-mxt_kyoiku02-100002607_04.pdf"
EBOARD_URL = "https://www.eboard.jp/list/7/"
OFFICIAL_PRACTICE = {
    1: "https://www.dokyoi.pref.hokkaido.lg.jp/hk/gks/ct/tangen1.html",
    2: "https://www.dokyoi.pref.hokkaido.lg.jp/hk/gks/ct/tangen2.html",
    3: "https://www.dokyoi.pref.hokkaido.lg.jp/hk/gks/ct/tangen3.html",
    4: "https://www.dokyoi.pref.hokkaido.lg.jp/hk/gks/ct/tangen4.html",
    5: "https://www.dokyoi.pref.hokkaido.lg.jp/hk/gks/ct/tangen5.html",
    6: "https://www.dokyoi.pref.hokkaido.lg.jp/hk/gks/ct/tangen6.html",
}

UNITS = [
    # ------------------------- 小学1年 -------------------------
    {
        "id": "g1-01", "grade": 1, "order": 1, "domain": "A 数と計算",
        "title": "10までのかず",
        "goal": "1〜10と0の意味、数え方、大小、数の分け方を理解する。",
        "point": "数を読むだけでなく、実物を数える・同じ数を別の分け方で表すところまでできると、その後のたし算が理解しやすくなります。",
        "prereq": "なし",
        "materials": [
            {"kind": "eboard", "label": "eboard：10までのかず", "url": "https://www.eboard.jp/content/158/"},
        ],
    },
    {
        "id": "g1-02", "grade": 1, "order": 2, "domain": "A 数と計算",
        "title": "たしざん",
        "goal": "『あわせる』『ふえる』場面をたし算の式で表し、1位数のたし算を計算する。",
        "point": "式だけを暗記するより、『3こあって2こ増えると5こ』のように場面と式を結びつけます。",
        "prereq": "10までのかず",
        "materials": [
            {"kind": "eboard", "label": "eboard：たしざん", "url": "https://www.eboard.jp/content/159/"},
        ],
    },
    {
        "id": "g1-03", "grade": 1, "order": 3, "domain": "A 数と計算",
        "title": "ひきざん",
        "goal": "『のこり』『ちがい』をひき算の式で表し、1位数のひき算を計算する。",
        "point": "『取った残り』と『どちらがいくつ多いか』は同じひき算でも意味が違います。場面を絵にすると理解が安定します。",
        "prereq": "10までのかず、たしざん",
        "materials": [
            {"kind": "eboard", "label": "eboard：ひきざん", "url": "https://www.eboard.jp/content/160/"},
        ],
    },
    {
        "id": "g1-04", "grade": 1, "order": 4, "domain": "A 数と計算",
        "title": "20までのかず・3つのかず",
        "goal": "20までの数を理解し、20までの加減や3つの数の計算に慣れる。",
        "point": "10といくつ、という見方を作るのが重要です。13を『10と3』と見られると繰り上がりにもつながります。",
        "prereq": "たしざん、ひきざん",
        "materials": [
            {"kind": "eboard", "label": "eboard：20までのかず", "url": "https://www.eboard.jp/content/161/"},
        ],
    },
    {
        "id": "g1-05", "grade": 1, "order": 5, "domain": "A 数と計算",
        "title": "10をこえるたし算・ひき算",
        "goal": "10のまとまりを使って、繰り上がりのたし算と繰り下がりのひき算を理解する。",
        "point": "8+7なら7を2と5に分けて10を先に作る、13-6なら10から6を引く、という10のまとまりが中心です。",
        "prereq": "10までの数の分解、20までのかず",
        "materials": [
            {"kind": "eboard", "label": "eboard：10よりおおきいたしざん、ひきざん", "url": "https://www.eboard.jp/content/162/"},
        ],
    },
    {
        "id": "g1-06", "grade": 1, "order": 6, "domain": "A 数と計算",
        "title": "100までのかず",
        "goal": "2位数の位取り、数の大小や順序、100までの数の構成を理解する。",
        "point": "『10がいくつと、1がいくつ』で2桁の数を見ることが、2年生の筆算につながります。",
        "prereq": "20までのかず",
        "materials": [
            {"kind": "eboard", "label": "eboard：100までのかず", "url": "https://www.eboard.jp/content/163/"},
        ],
    },
    {
        "id": "g1-07", "grade": 1, "order": 7, "domain": "A 数と計算",
        "title": "100までのかずのたし算・ひき算",
        "goal": "100までの数について、簡単な場合のたし算・ひき算を理解する。",
        "point": "十の位と一の位を分けて考える練習をします。筆算を急がず、数の仕組みから理解するのが大切です。",
        "prereq": "100までのかず",
        "materials": [
            {"kind": "eboard", "label": "eboard：100までのたしざん、ひきざん", "url": "https://www.eboard.jp/content/544/"},
        ],
    },
    {
        "id": "g1-08", "grade": 1, "order": 8, "domain": "A 数と計算",
        "title": "たし算・ひき算の文章題",
        "goal": "文章の場面から、たし算かひき算かを判断して式を立てる。",
        "point": "キーワードだけで判断せず、『何が最初にあって、どう変わったか』を絵や図で整理します。",
        "prereq": "たしざん、ひきざん",
        "materials": [
            {"kind": "eboard", "label": "eboard：たしざん、ひきざんのぶんしょうだい", "url": "https://www.eboard.jp/content/164/"},
        ],
    },
    {
        "id": "g1-09", "grade": 1, "order": 9, "domain": "B 図形",
        "title": "いろいろなかたち・かたちづくり・位置",
        "goal": "身の回りの形の特徴を捉え、形を組み合わせたり分けたりし、位置を言葉で表す。",
        "point": "『丸い』『平ら』『転がる』『積める』など、見た目だけでなく形の特徴を言葉にします。",
        "prereq": "なし",
        "materials": [
            {"kind": "youtube", "label": "群馬県公式：小1算数 かたちをつくろう", "url": "https://www.youtube.com/watch?v=MIZ_BV45K6k"},
        ],
    },
    {
        "id": "g1-10", "grade": 1, "order": 10, "domain": "C 測定",
        "title": "長さ・広さ・かさをくらべる",
        "goal": "長さ・広さ・かさを、直接比べたり同じ基準を使ったりして比較する。",
        "point": "比べるときは『端をそろえる』『同じ大きさのものを基準にする』という公平な比較が中心です。",
        "prereq": "数を数える",
        "materials": [
            {"kind": "youtube", "label": "いばスタ小学校：小1 ながさくらべ・ひろさくらべ", "url": "https://www.youtube.com/watch?v=M2h_K3UXN4s"},
            {"kind": "youtube", "label": "くろだちゃんねる：小1 かさくらべ", "url": "https://www.youtube.com/watch?v=EQFgCzqF8BQ"},
            {"kind": "web", "label": "黒田教育研究所：小1算数 15分教材（ながさ・かさ・ひろさ）", "url": "https://www.kurodalab.jp/math_videos/15minutes/15minutes_1/"},
        ],
    },
    {
        "id": "g1-11", "grade": 1, "order": 11, "domain": "C 測定",
        "title": "とけい・時刻",
        "goal": "時計を読み、日常生活の中で時刻を捉える。",
        "point": "短い針と長い針の役割を分け、まず『○時』『○時半』から安定させます。",
        "prereq": "60までの数を読む経験",
        "materials": [
            {"kind": "youtube", "label": "ごにチューブ：とけいのよみかた", "url": "https://www.youtube.com/watch?v=gdSYrlZof9c"},
        ],
    },
    {
        "id": "g1-12", "grade": 1, "order": 12, "domain": "D データの活用",
        "title": "かずを整理する・絵や図で表す",
        "goal": "ものを種類ごとに整理し、個数を絵や図で表して比べる。",
        "point": "ばらばらのものを種類ごとに並べ、同じ大きさ・同じ間隔で表すと、どれが多いか見やすくなります。",
        "prereq": "数を数える、大小を比べる",
        "materials": [
            {"kind": "web", "label": "すたぺんドリル：小1 かずしらべ無料プリント", "url": "https://startoo.co/workbook/84511/"},
            {"kind": "web", "label": "黒田教育研究所：小1 かずしらべ動画・プリント", "url": "https://www.kurodalab.jp/math_videos/15minutes/15minutes_1/"},
        ],
    },

    # ------------------------- 小学2年 -------------------------
    {
        "id": "g2-01", "grade": 2, "order": 1, "domain": "A 数と計算",
        "title": "1000までの数",
        "goal": "百の位を含む3位数、1000、数の大小や位取りを理解する。",
        "point": "10が10こで100、100が10こで1000という十進位取りを具体物と結びつけます。",
        "prereq": "100までのかず",
        "materials": [
            {"kind": "eboard", "label": "eboard：100より大きい数（3けたの数）", "url": "https://www.eboard.jp/content/170/"},
        ],
    },
    {
        "id": "g2-02", "grade": 2, "order": 2, "domain": "A 数と計算",
        "title": "2けたと1けたのたし算・ひき算",
        "goal": "2位数と1位数の加減を、位を意識して計算する。",
        "point": "一の位どうし、十の位どうしという位の考え方を明確にしてから筆算につなげます。",
        "prereq": "100までのかずの加減",
        "materials": [
            {"kind": "eboard", "label": "eboard：2けた+1けたのたしざん", "url": "https://www.eboard.jp/content/166/"},
            {"kind": "eboard", "label": "eboard：2けた-1けたのひきざん", "url": "https://www.eboard.jp/content/167/"},
        ],
    },
    {
        "id": "g2-03", "grade": 2, "order": 3, "domain": "A 数と計算",
        "title": "2けたの筆算",
        "goal": "2位数の加法・減法を筆算で行い、繰り上がり・繰り下がりを理解する。",
        "point": "数字を縦にそろえる理由は『同じ位どうしを計算するため』です。手順だけでなく位取りを確認します。",
        "prereq": "2けたと1けたの加減",
        "materials": [
            {"kind": "eboard", "label": "eboard：2けたのひっさん", "url": "https://www.eboard.jp/content/169/"},
        ],
    },
    {
        "id": "g2-04", "grade": 2, "order": 4, "domain": "A 数と計算",
        "title": "10000までの数",
        "goal": "千の位、10000までの数、数の大小や相対的な大きさを理解する。",
        "point": "位が増えても『10こ集まると1つ上の位』という仕組みは同じです。",
        "prereq": "1000までの数",
        "materials": [
            {"kind": "eboard", "label": "eboard：1000より大きい数", "url": "https://www.eboard.jp/content/177/"},
            {"kind": "youtube", "label": "ごにチューブ：1000より大きい数", "url": "https://www.youtube.com/watch?v=AtKiWq6KrGw"},
        ],
    },
    {
        "id": "g2-05", "grade": 2, "order": 5, "domain": "A 数と計算",
        "title": "計算のきまり・くふう",
        "goal": "たし算の順序や、かっこを使った計算の工夫を理解する。",
        "point": "答えが同じになるきまりを実際に確かめ、楽に計算するための道具として使います。",
        "prereq": "たし算・ひき算",
        "materials": [
            {"kind": "eboard", "label": "eboard：計算のくふう", "url": "https://www.eboard.jp/content/536/"},
            {"kind": "youtube", "label": "ごにチューブ：たし算・ひき算のきまり", "url": "https://www.youtube.com/watch?v=A767U1ae28o"},
        ],
    },
    {
        "id": "g2-06", "grade": 2, "order": 6, "domain": "C 測定",
        "title": "長さ cm・mm・m",
        "goal": "ものさしを使い、cm・mm・mで長さを測り、単位の関係を理解する。",
        "point": "0の位置をそろえること、1cm=10mm、1m=100cmを実際の長さと結びつけます。",
        "prereq": "長さくらべ",
        "materials": [
            {"kind": "eboard", "label": "eboard：ながさをはかる", "url": "https://www.eboard.jp/content/168/"},
        ],
    },
    {
        "id": "g2-07", "grade": 2, "order": 7, "domain": "C 測定",
        "title": "かさ L・dL・mL",
        "goal": "L・dL・mLを使ってかさを表し、単位の関係や簡単な計算を行う。",
        "point": "容器の見た目ではなく、同じ単位で測ると公平に比較できることを確認します。",
        "prereq": "かさくらべ",
        "materials": [
            {"kind": "eboard", "label": "eboard：かさをあらわす", "url": "https://www.eboard.jp/content/171/"},
        ],
    },
    {
        "id": "g2-08", "grade": 2, "order": 8, "domain": "C 測定",
        "title": "時刻と時間",
        "goal": "時刻を進めたり戻したりし、時間の長さや1日の時間を考える。",
        "point": "『時刻＝何時何分』『時間＝どれだけ長いか』を言葉で区別します。",
        "prereq": "時計の読み方",
        "materials": [
            {"kind": "eboard", "label": "eboard：時間と生活", "url": "https://www.eboard.jp/content/165/"},
            {"kind": "youtube", "label": "ごにチューブ：とけいのよみかた（復習）", "url": "https://www.youtube.com/watch?v=gdSYrlZof9c"},
        ],
    },
    {
        "id": "g2-09", "grade": 2, "order": 9, "domain": "B 図形",
        "title": "三角形・四角形・直角・長方形・正方形",
        "goal": "辺・頂点・直角を理解し、三角形・四角形・長方形・正方形・直角三角形を見分ける。",
        "point": "形の名前を暗記するより、辺の数・長さ・直角の有無という条件で見分けます。",
        "prereq": "いろいろなかたち",
        "materials": [
            {"kind": "eboard", "label": "eboard：三角形と四角形", "url": "https://www.eboard.jp/content/175/"},
        ],
    },
    {
        "id": "g2-10", "grade": 2, "order": 10, "domain": "B 図形",
        "title": "はこの形",
        "goal": "箱の面・辺・頂点に着目して、立体の特徴を捉える。",
        "point": "実物の箱を触りながら、面・辺・頂点を数えると理解しやすいです。",
        "prereq": "長方形・正方形",
        "materials": [
            {"kind": "eboard", "label": "eboard：はこの形", "url": "https://www.eboard.jp/content/539/"},
        ],
    },
    {
        "id": "g2-11", "grade": 2, "order": 11, "domain": "A 数と計算",
        "title": "かけ算の意味",
        "goal": "『1つ分の数×いくつ分』として、かけ算が使われる場面を理解する。",
        "point": "九九を覚える前に、同じ数のまとまりが何個あるか、という意味を図で理解します。",
        "prereq": "同じ数ずつまとめて数える",
        "materials": [
            {"kind": "eboard", "label": "eboard：かけ算と九九", "url": "https://www.eboard.jp/content/174/"},
        ],
    },
    {
        "id": "g2-12", "grade": 2, "order": 12, "domain": "A 数と計算",
        "title": "九九",
        "goal": "乗法九九を理解し、確実に使えるようにする。",
        "point": "暗唱だけでなく、2の段は2ずつ増えるなど、九九表の規則性も使います。",
        "prereq": "かけ算の意味",
        "materials": [
            {"kind": "youtube", "label": "ごにチューブ：九九 1・2・3の段", "url": "https://www.youtube.com/watch?v=322GitcxiSQ"},
            {"kind": "youtube", "label": "ごにチューブ：九九 7・8・9の段", "url": "https://www.youtube.com/watch?v=cEQu0K1ta70"},
            {"kind": "eboard", "label": "eboard：かけ算と九九", "url": "https://www.eboard.jp/content/174/"},
        ],
    },
    {
        "id": "g2-13", "grade": 2, "order": 13, "domain": "A 数と計算",
        "title": "分数のはじめ",
        "goal": "1/2、1/3など、全体を等しく分けた一つ分として分数を捉える。",
        "point": "分数では『同じ大きさに分ける』ことが最重要です。実物の紙や食べ物の図で確認します。",
        "prereq": "等分する経験",
        "materials": [
            {"kind": "eboard", "label": "eboard：分数（2年生）", "url": "https://www.eboard.jp/content/538/"},
        ],
    },
    {
        "id": "g2-14", "grade": 2, "order": 14, "domain": "D データの活用",
        "title": "表とグラフ",
        "goal": "身の回りの数量を整理し、表や簡単なグラフから特徴を読み取る。",
        "point": "表は数を正確に比べやすく、グラフは大小を見た目で捉えやすい、という役割の違いを学びます。",
        "prereq": "かずを整理する",
        "materials": [
            {"kind": "youtube", "label": "サカワチャンネル：小2 ひょうとグラフ", "url": "https://www.youtube.com/watch?v=vX30i4YzaQ4"},
        ],
    },
    {
        "id": "g2-15", "grade": 2, "order": 15, "domain": "A 数と計算",
        "title": "文章題（図を使う・3つの数・かけ算）",
        "goal": "図や数の関係を使って、複数の種類の文章題を解く。",
        "point": "分からないときは先に式を探さず、『分かっている数』『求めたい数』を図にします。",
        "prereq": "加減・かけ算",
        "materials": [
            {"kind": "eboard", "label": "eboard：文しょうだい（2年生）", "url": "https://www.eboard.jp/content/179/"},
        ],
    },

    # ------------------------- 小学3年 -------------------------
    {
        "id": "g3-01", "grade": 3, "order": 1, "domain": "A 数と計算",
        "title": "かけ算のおさらい・きまり",
        "goal": "0を含むかけ算や10をかける計算、乗法のきまりを使えるようにする。",
        "point": "九九を土台に、10倍や分けて計算する考え方へ広げます。",
        "prereq": "九九",
        "materials": [
            {"kind": "eboard", "label": "eboard：かけ算のおさらい", "url": "https://www.eboard.jp/content/540/"},
        ],
    },
    {
        "id": "g3-02", "grade": 3, "order": 2, "domain": "A 数と計算",
        "title": "わり算",
        "goal": "等分除・包含除の意味、わり算の式、九九を使った除法を理解する。",
        "point": "『同じ数ずつ分ける』と『何個ずつ取れるか』の2つの意味を図で区別します。",
        "prereq": "かけ算・九九",
        "materials": [
            {"kind": "eboard", "label": "eboard：わり算", "url": "https://www.eboard.jp/content/180/"},
            {"kind": "youtube", "label": "とある男が授業をしてみた：はじめてのわり算", "url": "https://www.youtube.com/watch?v=HXb2dy208ic"},
        ],
    },
    {
        "id": "g3-03", "grade": 3, "order": 3, "domain": "A 数と計算",
        "title": "3けたのたし算・ひき算（筆算）",
        "goal": "3位数や4位数の加法・減法を、位をそろえて正確に計算する。",
        "point": "繰り上がり・繰り下がりが複数の位に続いても、1つずつ位を処理します。",
        "prereq": "2けたの筆算",
        "materials": [
            {"kind": "eboard", "label": "eboard：3けたのたし算、ひき算（筆算）", "url": "https://www.eboard.jp/content/182/"},
        ],
    },
    {
        "id": "g3-04", "grade": 3, "order": 4, "domain": "A 数と計算",
        "title": "大きな数・10倍・100倍",
        "goal": "万の単位を含む大きな数と、10倍・100倍・1000倍、1/10の大きさを理解する。",
        "point": "位が1つ左へ動くと10倍、右へ動くと1/10という見方を位取り表で確かめます。",
        "prereq": "10000までの数",
        "materials": [
            {"kind": "eboard", "label": "eboard：大きな数と計算", "url": "https://www.eboard.jp/content/183/"},
        ],
    },
    {
        "id": "g3-05", "grade": 3, "order": 5, "domain": "C 測定",
        "title": "時間と時刻・秒",
        "goal": "時刻と時間の計算を行い、秒を含む時間の単位を理解する。",
        "point": "60秒=1分、60分=1時間という60進法に注意します。",
        "prereq": "2年生の時刻と時間",
        "materials": [
            {"kind": "eboard", "label": "eboard：時間と時こく", "url": "https://www.eboard.jp/content/184/"},
        ],
    },
    {
        "id": "g3-06", "grade": 3, "order": 6, "domain": "C 測定",
        "title": "長さ km",
        "goal": "kmとmの関係を理解し、長い距離を適切な単位で表す。",
        "point": "1km=1000mを、学校から駅までなど実際の距離の感覚と結びつけます。",
        "prereq": "m・cm・mm",
        "materials": [
            {"kind": "eboard", "label": "eboard：長さをあらわす km", "url": "https://www.eboard.jp/content/185/"},
        ],
    },
    {
        "id": "g3-07", "grade": 3, "order": 7, "domain": "A 数と計算",
        "title": "あまりのあるわり算",
        "goal": "あまりのある除法を計算し、あまりが除数より小さいことを理解する。",
        "point": "答えだけでなく、あまりが『割る数より小さい』かを必ず確かめます。",
        "prereq": "わり算・九九",
        "materials": [
            {"kind": "eboard", "label": "eboard：あまりのあるわり算", "url": "https://www.eboard.jp/content/187/"},
        ],
    },
    {
        "id": "g3-08", "grade": 3, "order": 8, "domain": "A 数と計算",
        "title": "かけ算の筆算",
        "goal": "2位数・3位数×1位数などの乗法を筆算で計算する。",
        "point": "一の位から順に計算し、繰り上がりを次の位へ渡す意味を理解します。",
        "prereq": "九九・位取り",
        "materials": [
            {"kind": "eboard", "label": "eboard：かけ算の筆算（×1けた）", "url": "https://www.eboard.jp/content/212/"},
        ],
    },
    {
        "id": "g3-09", "grade": 3, "order": 9, "domain": "C 測定",
        "title": "重さ g・kg・t",
        "goal": "g・kg・tで重さを表し、単位の関係や簡単な計算を理解する。",
        "point": "身近な物を持った感覚と数値を結びつけ、1kg=1000gを確認します。",
        "prereq": "測定の考え方",
        "materials": [
            {"kind": "eboard", "label": "eboard：重さをあらわす", "url": "https://www.eboard.jp/content/213/"},
        ],
    },
    {
        "id": "g3-10", "grade": 3, "order": 10, "domain": "A 数と計算",
        "title": "小数",
        "goal": "小数の意味と表し方、大小、小数のたし算・ひき算を理解する。",
        "point": "0.1を1つ分とする見方を作り、整数と同じ位取りの考え方で理解します。",
        "prereq": "10分の1の大きさ、位取り",
        "materials": [
            {"kind": "eboard", "label": "eboard：小数（3年生）", "url": "https://www.eboard.jp/content/216/"},
        ],
    },
    {
        "id": "g3-11", "grade": 3, "order": 11, "domain": "A 数と計算",
        "title": "分数",
        "goal": "分数の意味、単位分数のいくつ分、大小、簡単な加法・減法を理解する。",
        "point": "1/4が3こで3/4のように、『単位分数がいくつ分』で見ると計算にもつながります。",
        "prereq": "2年生の分数",
        "materials": [
            {"kind": "eboard", "label": "eboard：分数（3年生）", "url": "https://www.eboard.jp/content/214/"},
        ],
    },
    {
        "id": "g3-12", "grade": 3, "order": 12, "domain": "A 数と計算",
        "title": "□が入った式",
        "goal": "未知の数を□で表し、加減乗除の関係から□に入る数を求める。",
        "point": "逆算の手順だけでなく、式が表している数量の関係を図でも確認します。",
        "prereq": "加減乗除の意味",
        "materials": [
            {"kind": "eboard", "label": "eboard：□が入った式", "url": "https://www.eboard.jp/content/218/"},
        ],
    },
    {
        "id": "g3-13", "grade": 3, "order": 13, "domain": "B 図形",
        "title": "円と球",
        "goal": "円の中心・半径などの性質と、球の形の特徴を理解する。",
        "point": "コンパスは『中心から同じ長さの点を集める道具』と捉えると円の性質が理解しやすくなります。",
        "prereq": "長さを測る、基本図形",
        "materials": [
            {"kind": "eboard", "label": "eboard：円と球", "url": "https://www.eboard.jp/content/181/"},
        ],
    },
    {
        "id": "g3-14", "grade": 3, "order": 14, "domain": "B 図形",
        "title": "二等辺三角形・正三角形・角",
        "goal": "辺の長さに着目して二等辺三角形・正三角形を理解し、角を比べる。",
        "point": "見た目で判断せず、『同じ長さの辺が何本あるか』という条件で分類します。",
        "prereq": "三角形・辺・頂点",
        "materials": [
            {"kind": "eboard", "label": "eboard：三角形", "url": "https://www.eboard.jp/content/186/"},
        ],
    },
    {
        "id": "g3-15", "grade": 3, "order": 15, "domain": "D データの活用",
        "title": "表と棒グラフ",
        "goal": "データを分類整理し、表や棒グラフに表して特徴を読み取る。",
        "point": "棒の高さだけでなく、目盛りがいくつずつ増えるかを確認して読み取ります。",
        "prereq": "2年生の表とグラフ",
        "materials": [
            {"kind": "youtube", "label": "よしみん先生：棒グラフの書き方", "url": "https://www.youtube.com/watch?v=xTNc82HRgJU"},
            {"kind": "youtube", "label": "よしみん先生：棒グラフを読み取ろう", "url": "https://www.youtube.com/watch?v=3YtxQkLOyXg"},
        ],
    },
    {
        "id": "g3-16", "grade": 3, "order": 16, "domain": "A 数と計算",
        "title": "文章題（何倍・かけ算・わり算）",
        "goal": "複数の数量関係を整理し、かけ算・わり算を使う文章題を解く。",
        "point": "何倍か、1つ分はいくつか、全部はいくつか、の3つの量を図で整理します。",
        "prereq": "かけ算・わり算",
        "materials": [
            {"kind": "eboard", "label": "eboard：文章題（3年生）", "url": "https://www.eboard.jp/content/219/"},
        ],
    },
    {
        "id": "g3-17", "grade": 3, "order": 17, "domain": "A 数と計算",
        "title": "そろばん",
        "goal": "そろばんによる数の表し方と、簡単な加法・減法の仕組みに触れる。",
        "point": "珠の位置が位を表していることを理解し、まず数を正しく置けることを優先します。",
        "prereq": "位取り、たし算・ひき算",
        "materials": [
            {"kind": "youtube", "label": "長野県教育委員会：算数 小3 そろばん①", "url": "https://www.youtube.com/watch?v=NMkWPFyjWh8"},
        ],
    },
]


def _learning_unit(unit_id, grade, order, domain, title, goal, prereq, starter):
    """Create one consistent curriculum card for the expanded learning route."""
    materials = [
        {
            "kind": "activity",
            "label": "おうちで やってみよう",
            "instruction": starter,
        }
    ]
    if grade >= 1:
        materials.extend(
            [
                {
                    "kind": "web",
                    "label": "eboard：算数の映像授業",
                    "url": EBOARD_URL,
                },
                {
                    "kind": "web",
                    "label": f"北海道教育委員会：小学{grade}年 単元別問題",
                    "url": OFFICIAL_PRACTICE[grade],
                },
            ]
        )
    return {
        "id": unit_id,
        "grade": grade,
        "order": order,
        "domain": domain,
        "title": title,
        "goal": goal,
        "point": "できた速さではなく、物・絵・言葉・式を行き来して説明できることを大切にします。",
        "prereq": prereq,
        "materials": materials,
    }


# 5〜6歳は学校内容の前倒しではなく、具体物を使う数理体験から小1へ接続する。
_EXPANDED_CURRICULUM = {
    0: [
        ("p-01", "A 数と計算", "1から5まで", "物を一つずつ対応させ、5までの個数を正しく数える。", "なし", "積み木を1〜5個ならべ、指で一つずつ触りながら数えよう。"),
        ("p-02", "A 数と計算", "6から10まで", "10までの個数・順番・数字を結び付ける。", "1から5まで", "電車やミニカーを10個まで並べ、前から何番目かも言ってみよう。"),
        ("p-03", "A 数と計算", "おなじ・ちがう・どちらが多い", "一対一対応を使って、同じ・多い・少ないを比べる。", "10まで数える", "2列の物を一つずつ向かい合わせ、どちらが多いか確かめよう。"),
        ("p-04", "A 数と計算", "かずを分ける", "5や10を二つの数に分けたり、合わせたりする。", "10まで数える", "5個のおはじきを両手に隠して分け、右手と左手にいくつあるか当てよう。"),
        ("p-05", "A 数と計算", "ふえる・へる", "具体的な場面で、加えることと取り去ることを理解する。", "かずを分ける", "お皿の3個に2個を足す、5個から1個を取る動きを言葉にしよう。"),
        ("p-06", "B 図形", "かたちを見つける", "丸・三角・四角や立体の特徴を見つける。", "なし", "家の中から丸・三角・四角を三つずつ探し、似ている理由を話そう。"),
        ("p-07", "C 測定", "ながさ・おもさ・かさ", "直接比べて、長い・重い・多く入るを判断する。", "同じ・ちがう", "鉛筆の端をそろえて長さを比べ、比べ方が公平か確かめよう。"),
        ("p-08", "D データの活用", "なかま分け・ならび方", "色や形で分類し、簡単な規則を見つけて続ける。", "同じ・ちがう", "赤青赤青、丸三角丸三角の続きを作り、きまりを言葉にしよう。"),
        ("p-09", "C 測定", "くらしの時刻とお金", "生活の中で○時を読み、硬貨を区別する。", "10まで数える", "時計で出発時刻を探し、10円玉を5枚まで数えてみよう。"),
        ("p-10", "A 数と計算", "小1へのじゅんび", "数・形・比較を使う短い話を、自分の言葉で説明する。", "はじめの算数1〜9", "『3台の電車に2台きました』を物で作り、どう考えたか話そう。"),
    ],
    4: [
        ("g4-01", "A 数と計算", "大きな数", "億・兆までの整数と十進位取りを理解する。", "万までの数", "新聞や時刻表から大きな数を見つけ、位ごとに区切って読もう。"),
        ("g4-02", "A 数と計算", "わり算の筆算", "2〜3位数を1位数で割る筆算と余りを理解する。", "九九とわり算", "24個を3人で同じ数ずつ分け、式と筆算の意味を結び付けよう。"),
        ("g4-03", "A 数と計算", "2けたでわる筆算", "2〜3位数を2位数で割り、商を見積もる。", "1位数で割る筆算", "156÷24の答えが何桁になりそうか、計算前に見積もろう。"),
        ("g4-04", "A 数と計算", "計算のきまり", "四則混合、かっこ、交換・結合・分配の考えを使う。", "四則計算", "同じ答えになる二つの式を作り、どちらが計算しやすいか比べよう。"),
        ("g4-05", "A 数と計算", "がい数と見積もり", "四捨五入と概数を、目的に応じて使う。", "大きな数", "買い物の合計を百円単位で見積もり、実際の合計と比べよう。"),
        ("g4-06", "A 数と計算", "小数のしくみと計算", "小数の位取りと加減、整数との乗除を理解する。", "整数の位取り", "1mを10等分・100等分した長さを、小数で表そう。"),
        ("g4-07", "A 数と計算", "分数", "同分母分数の加減と、真分数・仮分数・帯分数を理解する。", "簡単な分数", "折り紙を同じ大きさに分け、3/4と5/4を図で表そう。"),
        ("g4-08", "B 図形", "角の大きさ", "度を単位として角を測り、描く。", "直角", "身の回りの角を直角より大きい・小さいに分け、分度器で確かめよう。"),
        ("g4-09", "B 図形", "垂直・平行と四角形", "直線の関係と、平行四辺形・ひし形・台形の特徴を理解する。", "三角形・四角形", "紙に平行な2本線を引き、いろいろな四角形を作ろう。"),
        ("g4-10", "B 図形", "直方体と立方体", "面・辺の関係、展開図、位置の表し方を理解する。", "箱の形", "空き箱を開いて展開図にし、向かい合う面に印を付けよう。"),
        ("g4-11", "C 測定", "面積", "面積の単位と長方形・正方形の公式を理解する。", "長さと掛け算", "方眼で長方形を作り、1cm²が何個あるか数えて公式につなげよう。"),
        ("g4-12", "D データの活用", "折れ線グラフと表", "変化を折れ線グラフに表し、特徴を読む。", "棒グラフ", "一日の気温を表にし、点を結んで変化が大きい所を探そう。"),
        ("g4-13", "D データの活用", "変わり方", "伴って変わる二つの量を表や式で調べる。", "表と式", "正方形を横に増やすと棒の本数がどう変わるか、表にしよう。"),
        ("g4-14", "A 数と計算", "そろばん", "そろばんで大きな数や小数を表し、加減する。", "位取り", "一の位を決め、同じ数字を整数と小数で置き比べよう。"),
    ],
    5: [
        ("g5-01", "A 数と計算", "整数と小数", "整数・小数を10倍、100倍、1/10、1/100にした関係を理解する。", "小数の位取り", "3.47の数字カードを動かし、10倍と1/10の数を作ろう。"),
        ("g5-02", "A 数と計算", "小数のかけ算", "小数×整数、小数×小数の意味と筆算を理解する。", "整数の掛け算・小数", "1m80円のひも2.5m分を図にして、式の意味を説明しよう。"),
        ("g5-03", "A 数と計算", "小数のわり算", "小数÷整数、小数÷小数の意味と筆算を理解する。", "整数の割り算・小数", "2.4Lを0.6Lずつ分ける場面を図にしよう。"),
        ("g5-04", "A 数と計算", "倍数と約数", "倍数・約数、公倍数・公約数を理解する。", "掛け算・割り算", "12個と18個を余りなく同じ人数に配れる人数を全部探そう。"),
        ("g5-05", "A 数と計算", "分数の大きさとたし算・ひき算", "通分・約分を使い、異分母分数を加減する。", "同分母分数", "1/2と2/3を同じ大きさの図に直して比べよう。"),
        ("g5-06", "A 数と計算", "分数と小数・整数", "分数・小数・整数の関係と、分数×÷整数を理解する。", "分数と小数", "3÷4を図・分数・小数の三つで表そう。"),
        ("g5-07", "C 測定", "体積", "直方体・立方体の体積と単位の関係を理解する。", "面積・直方体", "1cm角の積み木を箱状に並べ、縦×横×高さとの関係を探そう。"),
        ("g5-08", "C 測定", "平均", "平均の意味を、ならす考えで理解する。", "割り算", "高さの違う積み木の列を、合計を変えず同じ高さにならそう。"),
        ("g5-09", "C 測定", "単位量あたりの大きさ", "混み具合や人口密度を、1当たりの量で比べる。", "平均・割り算", "面積と人数が違う二つの部屋の混み具合を比べる方法を考えよう。"),
        ("g5-10", "B 図形", "合同な図形", "合同の意味と対応する辺・角を理解し、作図する。", "三角形・四角形・角", "同じ形の紙を裏返したり回したりし、重なる条件を話そう。"),
        ("g5-11", "B 図形", "図形の角", "三角形・四角形・多角形の角の和を理解する。", "角の大きさ", "紙の三角形の角を切って一点に集め、何度になるか確かめよう。"),
        ("g5-12", "B 図形", "面積", "平行四辺形・三角形・台形・ひし形の面積を求める。", "長方形の面積", "平行四辺形を切って長方形に変え、公式の理由を説明しよう。"),
        ("g5-13", "B 図形", "正多角形と円", "正多角形の性質と円周率の意味を理解する。", "円・角", "円を使って正六角形を描き、辺の長さを比べよう。"),
        ("g5-14", "B 図形", "角柱と円柱", "角柱・円柱の構成要素と見取図・展開図を理解する。", "直方体・円", "箱や筒の面を調べ、底面と側面の形を記録しよう。"),
        ("g5-15", "D データの活用", "割合と帯・円グラフ", "割合・百分率を理解し、帯グラフや円グラフを読む。", "小数の割り算", "10個の物を色別に分け、全体を1として割合を表そう。"),
        ("g5-16", "D データの活用", "変わり方", "簡単な比例関係を表・式から見つける。", "4年の変わり方", "同じ値段の品物の個数と代金を表にし、関係を式にしよう。"),
    ],
    6: [
        ("g6-01", "A 数と計算", "文字と式", "数量をxなどの文字を使った式に表す。", "四則混合・変わり方", "値段が分からない品物をx円として、合計代金を式にしよう。"),
        ("g6-02", "A 数と計算", "分数のかけ算", "分数×分数の意味と計算方法を理解する。", "分数×整数・約分", "2/3mの1/2を図で表し、式と答えを結び付けよう。"),
        ("g6-03", "A 数と計算", "分数のわり算", "分数÷分数の意味と計算方法を理解する。", "分数の掛け算", "3/4Lを1/8Lずつ分ける場面を図と式で表そう。"),
        ("g6-04", "D データの活用", "比", "二つの量の割合を比で表し、等しい比を理解する。", "割合・分数", "同じ味になるジュースと水の組合せを複数作り、比で表そう。"),
        ("g6-05", "D データの活用", "比例と反比例", "比例・反比例を表、式、グラフで表す。", "5年の変わり方", "面積が24cm²の長方形で、縦と横の関係を表にしよう。"),
        ("g6-06", "C 測定", "速さ", "速さ・道のり・時間の関係を理解する。", "単位量あたり・時間", "同じ道のりを進んだ二人を、時間から比べて説明しよう。"),
        ("g6-07", "B 図形", "対称な図形", "線対称・点対称の性質を理解し、作図する。", "合同な図形", "紙を折って切った形から、対称の軸と対応する点を探そう。"),
        ("g6-08", "B 図形", "円の面積", "円の面積の公式と、その根拠を理解する。", "円周率・面積", "円を細かい扇形に分けて並べ替え、どんな形に近づくか考えよう。"),
        ("g6-09", "B 図形", "角柱・円柱の体積", "柱体の体積を底面積×高さで求める。", "直方体の体積・面積", "同じ底面の箱を積み、底面積×高さになる理由を話そう。"),
        ("g6-10", "B 図形", "拡大図と縮図", "対応する辺・角を使って拡大図・縮図を理解する。", "比・合同", "簡単な地図で1cmが実際の何mかを決め、距離を求めよう。"),
        ("g6-11", "D データの活用", "場合の数", "重なりや落ちがないよう、順序よく組合せを調べる。", "表・図", "3色から2色を選ぶ方法を、表や樹形図ですべて書こう。"),
        ("g6-12", "D データの活用", "データの調べ方", "代表値、度数分布、柱状グラフを使ってデータを考察する。", "平均・グラフ", "二つの組の記録を、平均だけでなく散らばりも見て比べよう。"),
        ("g6-13", "C 測定", "およその面積・体積と単位", "身近な形を基本図形とみなし、概測する。", "面積・体積・概数", "手のひらの面積を長方形や三角形とみなして見積もろう。"),
        ("g6-14", "A 数と計算", "小学校算数のまとめ", "数・量・図形・データを組み合わせて問題を解き、説明する。", "小1〜小6の主要単元", "一つの問題を図・式・言葉の三通りで説明し、最も伝わる方法を選ぼう。"),
    ],
}

for _grade, _rows in _EXPANDED_CURRICULUM.items():
    for _order, (_unit_id, _domain, _title, _goal, _prereq, _starter) in enumerate(_rows, 1):
        UNITS.append(
            _learning_unit(
                _unit_id,
                _grade,
                _order,
                _domain,
                _title,
                _goal,
                _prereq,
                _starter,
            )
        )

COURSE_LABELS = {
    0: "はじめ（5〜6歳）",
    1: "小1",
    2: "小2",
    3: "小3",
    4: "小4",
    5: "小5",
    6: "小6",
}

DOMAIN_SHORT = {
    "A 数と計算": "数と計算",
    "B 図形": "図形",
    "C 測定": "測定",
    "D データの活用": "データ",
}


def inject_css():
    st.markdown(
        """
        <style>
        :root {
            --kid-blue: #5b78d6;
            --kid-blue-strong: #465fb5;
            --kid-blue-soft: #f3f6ff;
            --kid-line: #d9e1f5;
            --kid-line-strong: #c7d3f0;
            --kid-yellow: #fff8dc;
            --kid-ink: #27364f;
            --kid-muted: #6f7d96;
            --kid-surface: #ffffff;
            --kid-surface-soft: #fbfcff;
        }

        /* Give the app enough breathing room without leaving a large empty cap. */
        .block-container {
            padding-top: 3.35rem !important;
            padding-bottom: 3rem !important;
            max-width: 980px;
        }

        /* Typography hierarchy: strong enough for children, but not heavy everywhere. */
        .main-title {
            font-size: 2.15rem;
            font-weight: 800;
            line-height: 1.18;
            letter-spacing: .005em;
            color: var(--kid-ink);
            margin-bottom: .25rem;
        }
        .home-question {
            font-size: 1.65rem;
            font-weight: 800;
            line-height: 1.3;
            color: var(--kid-ink);
            margin: .85rem 0 .4rem 0;
        }
        .subtle {color: var(--kid-muted); font-size: .94rem;}
        .progress-line {
            font-size: 1rem;
            font-weight: 700;
            color: var(--kid-muted);
            margin: .45rem 0 .3rem 0;
        }

        /* Study-page information cards use the same visual weight as the home cards. */
        .unit-card {
            border: 1.5px solid var(--kid-line);
            border-radius: 18px;
            padding: 18px 20px;
            margin: 10px 0 14px 0;
            background: var(--kid-surface-soft);
            box-shadow: 0 2px 8px rgba(39,54,79,.035);
        }
        .unit-title {
            font-size: 1.45rem;
            font-weight: 800;
            line-height: 1.35;
            margin-bottom: .45rem;
            color: var(--kid-ink);
        }
        .chip {
            display: inline-block;
            border: 1px solid var(--kid-line-strong);
            border-radius: 999px;
            padding: 4px 10px;
            font-size: .8rem;
            font-weight: 650;
            margin-right: 6px;
            background: var(--kid-blue-soft);
            color: var(--kid-blue-strong);
        }
        .goal-box {
            border-radius: 14px;
            padding: 13px 15px;
            background: var(--kid-yellow);
            margin-top: 12px;
            font-size: 1rem;
            line-height: 1.65;
            color: var(--kid-ink);
        }
        .tiny {font-size:.82rem; color:var(--kid-muted);}
        div[data-testid="stMetricValue"] {font-size:1.2rem;}

        /* Grade choice: medium weight, same border language as unit cards. */
        .st-key-home_grade [role="radiogroup"] {
            gap: .5rem;
            flex-wrap: wrap;
        }
        .st-key-home_grade [role="radiogroup"] label {
            border: 1.5px solid var(--kid-line);
            border-radius: 14px;
            padding: .45rem .85rem;
            min-width: 92px;
            min-height: 52px;
            justify-content: center;
            background: var(--kid-surface);
            color: var(--kid-ink);
            font-size: 1.05rem;
            font-weight: 700;
            box-shadow: 0 1px 4px rgba(39,54,79,.025);
        }
        .st-key-home_grade [role="radiogroup"] label p {
            font-size: 1.05rem !important;
            font-weight: 700 !important;
        }

        /* Home unit buttons: one calm card system, equal height and balanced type/border weight. */
        .st-key-unit_picker_grid button {
            height: 108px !important;
            min-height: 108px !important;
            max-height: 108px !important;
            border-radius: 18px !important;
            border: 1.5px solid var(--kid-line) !important;
            background: var(--kid-surface) !important;
            color: var(--kid-ink) !important;
            text-align: left !important;
            justify-content: flex-start !important;
            align-items: center !important;
            padding: 1rem 1.15rem !important;
            box-shadow: 0 2px 7px rgba(39,54,79,.04) !important;
            overflow: hidden !important;
            transition: border-color .14s ease, background .14s ease, transform .08s ease, box-shadow .14s ease;
        }
        .st-key-unit_picker_grid button p,
        .st-key-unit_picker_grid div[data-testid="stButton"] button p {
            width: 100% !important;
            margin: 0 !important;
            white-space: normal !important;
            overflow-wrap: anywhere !important;
            font-size: 1.34rem !important;
            font-weight: 720 !important;
            line-height: 1.35 !important;
            letter-spacing: 0 !important;
        }
        .st-key-unit_picker_grid button:hover {
            border-color: var(--kid-line-strong) !important;
            background: var(--kid-blue-soft) !important;
            box-shadow: 0 4px 12px rgba(39,54,79,.06) !important;
        }
        .st-key-unit_picker_grid button:active {
            transform: scale(.992);
        }

        /* Primary study path: the material itself is the tap target. */
        .unit-card-compact {
            padding-top: 15px;
            padding-bottom: 15px;
            margin-bottom: 10px;
        }
        .st-key-study_materials {
            margin-top: 4px;
            margin-bottom: 10px;
        }
        .st-key-study_materials a {
            min-height: 66px !important;
            border-radius: 16px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: flex-start !important;
            padding: .9rem 1.05rem !important;
            text-align: left !important;
        }
        .st-key-study_materials a p {
            font-size: 1.08rem !important;
            font-weight: 760 !important;
            line-height: 1.35 !important;
            white-space: normal !important;
        }
        .material-title {
            font-size: 1.08rem;
            font-weight: 760;
            color: var(--kid-ink);
            margin: .2rem 0 .55rem 0;
        }
        .material-gap { height: .5rem; }
        .st-key-study_practice { margin-top: 10px; margin-bottom: 8px; }
        .st-key-study_practice a {
            min-height: 54px !important;
            border-radius: 14px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            font-weight: 720 !important;
        }

        /* Each lesson is one compact learning card: lesson -> problem -> done. */
        [class*="st-key-material_row_"] {
            border: 1.5px solid var(--kid-line);
            border-radius: 18px;
            padding: 12px 12px 10px 12px;
            margin: 8px 0 12px 0;
            background: var(--kid-surface-soft);
            box-shadow: 0 2px 8px rgba(39,54,79,.035);
        }
        [class*="st-key-lesson_action_"] a,
        [class*="st-key-problem_action_"] a,
        [class*="st-key-done_action_"] button {
            border-radius: 14px !important;
            border: 1.5px solid var(--kid-line-strong) !important;
            box-shadow: none !important;
            font-weight: 740 !important;
        }
        [class*="st-key-lesson_action_"] a {
            min-height: 62px !important;
            justify-content: flex-start !important;
            text-align: left !important;
            padding: .85rem 1rem !important;
            background: var(--kid-blue-soft) !important;
            color: var(--kid-ink) !important;
        }
        [class*="st-key-lesson_action_"] a p {
            font-size: 1.12rem !important;
            font-weight: 760 !important;
            line-height: 1.35 !important;
            white-space: normal !important;
        }
        [class*="st-key-problem_action_"] a,
        [class*="st-key-done_action_"] button {
            min-height: 48px !important;
            justify-content: center !important;
            background: #fff !important;
            color: var(--kid-blue-strong) !important;
        }
        [class*="st-key-problem_action_"] a p,
        [class*="st-key-done_action_"] button p {
            font-size: .98rem !important;
            font-weight: 740 !important;
        }
        /* Once 'できた' is tapped, the lesson, its problem, and the done button change together. */
        [class*="st-key-material_row_done_"] {
            border-color: #9bcfad !important;
            background: #f2fbf5 !important;
        }
        [class*="st-key-material_row_done_"] a,
        [class*="st-key-material_row_done_"] button {
            background: #e6f7eb !important;
            border-color: #91c9a4 !important;
            color: #287344 !important;
        }
        [class*="st-key-material_row_done_"] a:hover,
        [class*="st-key-material_row_done_"] button:hover {
            background: #dcf3e3 !important;
            border-color: #78bb90 !important;
        }
        /* A unit on the top page turns green only when all of its materials are complete. */
        [class*="st-key-home_unit_done_"] button {
            background: #eaf8ee !important;
            border-color: #96ccaa !important;
            color: #287344 !important;
        }

        /* Study actions use the same radius and weight, avoiding oversized heavy controls. */
        .st-key-complete_action {
            margin-top: 8px;
        }
        .st-key-complete_action button {
            min-height: 44px !important;
            border-radius: 14px !important;
            font-weight: 700 !important;
            background: var(--kid-surface) !important;
            color: var(--kid-blue-strong) !important;
            border: 1.5px solid var(--kid-line-strong) !important;
        }
        .st-key-study_home_top button,
        .st-key-study_home_bottom button {
            min-height: 56px !important;
            border-radius: 16px !important;
            border-width: 1.5px !important;
            font-size: 1.05rem !important;
            font-weight: 750 !important;
            padding: 10px 18px !important;
        }
        .st-key-study_home_top {margin-bottom: 10px;}
        .st-key-study_home_bottom {margin-top: 16px;}

        .starter-card {
            border: 1.5px solid #f0cf7a;
            border-radius: 16px;
            padding: 15px 16px;
            background: #fffaf0;
            color: var(--kid-ink);
            font-size: 1.05rem;
            line-height: 1.7;
            margin-bottom: 10px;
        }
        .starter-label {
            color: #8a6414;
            font-size: .88rem;
            font-weight: 800;
            margin-bottom: .25rem;
        }
        .next-unit {
            border-left: 5px solid #6f8ee8;
            border-radius: 12px;
            padding: 10px 13px;
            background: var(--kid-blue-soft);
            color: var(--kid-ink);
            margin: .6rem 0 1rem 0;
            font-weight: 700;
        }
        .ai-answer {
            border: 1.5px solid var(--kid-line);
            border-radius: 16px;
            padding: 14px 16px;
            background: #fff;
            line-height: 1.75;
        }

        @media (max-width: 700px) {
            .block-container {
                padding-top: 3.55rem !important;
                padding-left: .8rem !important;
                padding-right: .8rem !important;
            }
            .main-title {font-size: 2rem;}
            .home-question {font-size: 1.55rem; margin-top: .75rem;}
            .unit-card {padding: 15px 15px; border-radius: 16px;}
            .unit-title {font-size: 1.3rem;}
            .st-key-home_grade [role="radiogroup"] {gap: .35rem;}
            .st-key-home_grade [role="radiogroup"] label {
                min-width: 84px;
                min-height: 50px;
                padding: .4rem .65rem;
                font-size: 1rem;
            }
            .st-key-home_grade [role="radiogroup"] label p {
                font-size: 1rem !important;
                font-weight: 700 !important;
            }
            .st-key-unit_picker_grid button {
                height: 102px !important;
                min-height: 102px !important;
                max-height: 102px !important;
                border-radius: 16px !important;
                padding: .85rem .9rem !important;
            }
            .st-key-unit_picker_grid button p,
            .st-key-unit_picker_grid div[data-testid="stButton"] button p {
                font-size: 1.2rem !important;
                font-weight: 720 !important;
                line-height: 1.34 !important;
            }
            [class*="st-key-material_row_"] {
                border-radius: 16px;
                padding: 10px;
                margin-bottom: 10px;
            }
            [class*="st-key-lesson_action_"] a {
                min-height: 60px !important;
                padding: .78rem .85rem !important;
            }
            [class*="st-key-lesson_action_"] a p {
                font-size: 1.06rem !important;
            }
            [class*="st-key-problem_action_"] a,
            [class*="st-key-done_action_"] button {
                min-height: 48px !important;
            }
            .st-key-study_home_top button,
            .st-key-study_home_bottom button {
                min-height: 58px !important;
                font-size: 1.08rem !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

def get_api_key():
    key = st.session_state.get("openai_api_key", "").strip()
    if key:
        return key
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if key:
        return key
    try:
        key = str(st.secrets["OPENAI_API_KEY"]).strip()
        return key
    except Exception:
        return ""


def get_client():
    key = get_api_key()
    if not key or OpenAI is None:
        return None
    return OpenAI(api_key=key)


def ask_openai(text, unit, source_context=None, source_label=None, image_bytes=None, image_mime=None):
    client = get_client()
    if client is None:
        raise RuntimeError("OpenAI APIキーが設定されていません。")

    grade = int(unit["grade"])
    learner = "5〜6歳" if grade == 0 else f"小学{grade}年生"
    base_instructions = f"""
あなたは{learner}専任の算数サポーターです。
学習単元は「{unit['title']}」です。
到達目標は「{unit['goal']}」です。

ルール:
- {learner}が理解できる日本語を使う。
- 1文を短くし、難しい専門用語を避ける。
- 正解を最初に言わず、短いヒントを一つだけ出して本人の答えを待つ。
- 間違いを責めない。どこまでは合っているかを明確にする。
- 5〜6歳には、積み木・おはじき・指など具体物を使う遊びを優先する。
- 必要なら図の代わりに、●や□、簡単な数直線を使う。
- 文章題では『分かっていること』『求めること』『式』を分ける。
- 学年外の高度な公式へ飛ばない。
- 返答は一度に長くしすぎず、原則120字以内にする。
""".strip()

    if source_context:
        base_instructions += "\n- 教材について答えるときは、下の取得内容を優先し、教材にない説明を教材内の内容として作らない。"
        text = f"""参照教材: {source_label or '教材'}\n教材から取得した内容:\n{source_context[:22000]}\n\n子どもの質問:\n{text}"""

    if image_bytes is not None:
        encoded = base64.b64encode(image_bytes).decode("utf-8")
        mime = image_mime or "image/jpeg"
        data_uri = f"data:{mime};base64,{encoded}"
        prompt = f"""
この答案画像を添削してください。
1. 問題文と子どもの答えを読み取る。
2. 合っているところを短く示す。
3. 最初に間違った箇所があれば、その箇所だけを具体的に示す。
4. 子どもが自分で直せるヒントを1つ出す。
5. 最後に正しい考え方を短く説明する。
6. 画像が不鮮明で読めない部分は、推測せず『読めません』と書く。

追加の依頼: {text}
""".strip()
        response = client.responses.create(
            model="gpt-5.6-luna",
            instructions=base_instructions,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {"type": "input_image", "image_url": data_uri},
                    ],
                }
            ],
        )
    else:
        response = client.responses.create(
            model="gpt-5.6-luna",
            instructions=base_instructions,
            input=text,
        )
    return response.output_text


def extract_youtube_id(url):
    if not url:
        return None
    patterns = [
        r"youtu\.be/([A-Za-z0-9_-]{11})",
        r"youtube\.com/watch\?.*?v=([A-Za-z0-9_-]{11})",
        r"youtube\.com/shorts/([A-Za-z0-9_-]{11})",
        r"youtube\.com/embed/([A-Za-z0-9_-]{11})",
    ]
    for pattern in patterns:
        m = re.search(pattern, url)
        if m:
            return m.group(1)
    return None


def fetch_youtube_transcript(video_id):
    if YouTubeTranscriptApi is None:
        raise RuntimeError("youtube-transcript-api がインストールされていません。")

    languages = ["ja", "ja-JP", "en"]
    errors = []

    # youtube-transcript-api 1.x
    try:
        api = YouTubeTranscriptApi()
        fetched = api.fetch(video_id, languages=languages)
        texts = []
        for item in fetched:
            if hasattr(item, "text"):
                texts.append(item.text)
            elif isinstance(item, dict):
                texts.append(item.get("text", ""))
        text = " ".join(x for x in texts if x).strip()
        if text:
            return text
    except Exception as exc:
        errors.append(str(exc))

    # older versions fallback
    try:
        data = YouTubeTranscriptApi.get_transcript(video_id, languages=languages)
        text = " ".join(item.get("text", "") for item in data).strip()
        if text:
            return text
    except Exception as exc:
        errors.append(str(exc))

    raise RuntimeError("字幕を取得できませんでした。字幕が無い、取得制限がある、または動画側の設定で取得できない可能性があります。")


class _VisibleTextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript"}:
            self.skip_depth += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"} and self.skip_depth:
            self.skip_depth -= 1

    def handle_data(self, data):
        if self.skip_depth == 0:
            text = " ".join(data.split())
            if text:
                self.parts.append(text)


def fetch_web_text(url):
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; SansuNavi/1.0)"})
    with urlopen(req, timeout=12) as response:
        raw = response.read(1_500_000)
        charset = response.headers.get_content_charset() or "utf-8"
    html = raw.decode(charset, errors="replace")
    parser = _VisibleTextParser()
    parser.feed(html)
    text = "\n".join(parser.parts)
    if not text.strip():
        raise RuntimeError("教材ページの本文を取得できませんでした。")
    return text[:30000]


def material_type_label(kind):
    return {
        "activity": "体験ミニ学習",
        "eboard": "映像授業＋確認問題",
        "youtube": "解説動画",
        "web": "Web教材・プリント",
    }.get(kind, "教材")


def material_note(kind):
    return {
        "activity": "身近な物を使って、考え方を体験します。",
        "eboard": "この単元の主教材として使用します。短い映像授業と確認問題があります。",
        "youtube": "別の見せ方で理解を補う補助動画です。",
        "web": "図・プリント・補助解説として使います。",
    }.get(kind, "この単元の補助教材です。")


EBOARD_DIRECT_LESSONS = {
    # Verified against the current eboard unit page. This also guarantees a useful
    # first-load path if eboard temporarily blocks server-side index fetching.
    "https://www.eboard.jp/content/158/": [
        {
            "order": 1,
            "title": "1から5までのかず",
            "video_url": "https://www.eboard.jp/content/158/v/1/",
            "question_url": "https://www.eboard.jp/content/158/q/1/1/",
        },
        {
            "order": 2,
            "title": "6から10までのかず、0（れい）",
            "video_url": "https://www.eboard.jp/content/158/v/2/",
            "question_url": "https://www.eboard.jp/content/158/q/2/1/",
        },
        {
            "order": 3,
            "title": "かずをわける",
            "video_url": "https://www.eboard.jp/content/158/v/3/",
            "question_url": "https://www.eboard.jp/content/158/q/3/1/",
        },
    ],
}


class _EboardUnitIndexParser(HTMLParser):
    """Read the lesson rows from an eboard content index without depending on CSS classes."""

    def __init__(self):
        super().__init__()
        self._heading_depth = 0
        self._heading_parts = []
        self._current_heading = ""
        self._anchor_href = None
        self._anchor_parts = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        tag = str(tag or "").lower()
        if tag in {"h2", "h3", "h4"}:
            self._heading_depth += 1
            if self._heading_depth == 1:
                self._heading_parts = []
        if tag == "a":
            href = dict(attrs).get("href")
            self._anchor_href = str(href or "").strip() or None
            self._anchor_parts = []

    def handle_data(self, data):
        text = " ".join(str(data or "").split())
        if not text:
            return
        if self._heading_depth:
            self._heading_parts.append(text)
        if self._anchor_href is not None:
            self._anchor_parts.append(text)

    def handle_endtag(self, tag):
        tag = str(tag or "").lower()
        if tag in {"h2", "h3", "h4"} and self._heading_depth:
            self._heading_depth -= 1
            if self._heading_depth == 0:
                self._current_heading = " ".join(self._heading_parts).strip()
        if tag == "a" and self._anchor_href is not None:
            self.links.append(
                {
                    "href": self._anchor_href,
                    "text": " ".join(self._anchor_parts).strip(),
                    "heading": self._current_heading,
                }
            )
            self._anchor_href = None
            self._anchor_parts = []


def _normalize_eboard_unit_url(url):
    value = str(url or "").strip()
    if not value:
        return ""
    parsed = urlparse(value)
    path = parsed.path or "/"
    if not path.endswith("/"):
        path += "/"
    return f"{parsed.scheme or 'https'}://{parsed.netloc}{path}"


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_eboard_direct_lessons(url):
    """Return eboard's individual video + matching confirmation-problem links."""
    unit_url = _normalize_eboard_unit_url(url)
    fallback = [dict(item) for item in EBOARD_DIRECT_LESSONS.get(unit_url, [])]

    try:
        req = Request(unit_url, headers={"User-Agent": "Mozilla/5.0 (compatible; SansuNavi/1.0)"})
        with urlopen(req, timeout=10) as response:
            raw = response.read(1_500_000)
            charset = response.headers.get_content_charset() or "utf-8"
        html_text = raw.decode(charset, errors="replace")
        parser = _EboardUnitIndexParser()
        parser.feed(html_text)

        base_match = re.search(r"/content/(\d+)/", urlparse(unit_url).path or "")
        content_id = base_match.group(1) if base_match else ""
        lessons = {}
        questions = {}
        for link in parser.links:
            absolute = urljoin(unit_url, link.get("href") or "")
            path = urlparse(absolute).path or ""
            video_match = re.fullmatch(r"/content/(\d+)/v/(\d+)/?", path)
            question_match = re.fullmatch(r"/content/(\d+)/q/(\d+)/1/?", path)
            if video_match and (not content_id or video_match.group(1) == content_id):
                number = int(video_match.group(2))
                heading = str(link.get("heading") or "").strip()
                title = re.sub(r"^\s*\d+[.．、)]?\s*", "", heading).strip()
                if not title or title in {"動画一覧", "もくじ"}:
                    title = str(link.get("text") or "").strip()
                lessons[number] = {
                    "order": number,
                    "title": title or f"教材 {number}",
                    "video_url": absolute,
                    "question_url": "",
                }
            elif question_match and (not content_id or question_match.group(1) == content_id):
                questions[int(question_match.group(2))] = absolute

        result = []
        for number in sorted(lessons):
            item = dict(lessons[number])
            item["question_url"] = questions.get(number, "")
            result.append(item)
        if result:
            return result
    except Exception:
        pass

    return fallback


def _safe_widget_token(value):
    return re.sub(r"[^0-9A-Za-z_]+", "_", str(value or "")).strip("_") or "item"


def _lesson_completion_key(unit_id, material_index, lesson_number):
    return f"{unit_id}:eboard:{int(material_index)}:lesson:{int(lesson_number)}"


def _material_completion_key(unit_id, material_index, kind):
    return f"{unit_id}:{str(kind or 'material').lower()}:{int(material_index)}"


def unit_material_completion_keys(unit):
    keys = []
    for material_index, material in enumerate(list((unit or {}).get("materials") or [])):
        kind = str(material.get("kind") or "").strip().lower()
        if kind == "eboard":
            lessons = fetch_eboard_direct_lessons(material.get("url"))
            if lessons:
                keys.extend(
                    _lesson_completion_key(unit.get("id"), material_index, int(lesson.get("order") or index + 1))
                    for index, lesson in enumerate(lessons)
                )
            else:
                keys.append(_material_completion_key(unit.get("id"), material_index, kind))
        else:
            keys.append(_material_completion_key(unit.get("id"), material_index, kind))
    return keys


def sync_unit_completion(unit, completed_units, completed_materials):
    keys = unit_material_completion_keys(unit)
    unit_id = str((unit or {}).get("id") or "")
    if unit_id and keys and all(key in completed_materials for key in keys):
        completed_units.add(unit_id)
    elif unit_id:
        completed_units.discard(unit_id)


def migrate_legacy_unit_completion(unit, completed_units, completed_materials):
    """Preserve progress from older versions that had one 'できた' button per unit."""
    unit_id = str((unit or {}).get("id") or "")
    if not unit_id or unit_id not in completed_units:
        return
    keys = unit_material_completion_keys(unit)
    if keys and not any(key in completed_materials for key in keys):
        completed_materials.update(keys)


def _toggle_material_done(completion_key, unit, completed_units, completed_materials):
    if completion_key in completed_materials:
        completed_materials.discard(completion_key)
    else:
        completed_materials.add(completion_key)
    sync_unit_completion(unit, completed_units, completed_materials)


def _render_done_action(completion_key, unit, completed_units, completed_materials, token):
    done = completion_key in completed_materials
    state = "done" if done else "open"
    with st.container(key=f"done_action_{state}_{token}"):
        if st.button(
            "✓ できた" if done else "○ できた",
            use_container_width=True,
            key=f"done_material_{token}",
        ):
            _toggle_material_done(completion_key, unit, completed_units, completed_materials)
            st.rerun()


def _render_eboard_material(unit, material, material_index, completed_units, completed_materials):
    url = str(material.get("url") or "").strip()
    lessons = fetch_eboard_direct_lessons(url)
    if not lessons:
        completion_key = _material_completion_key(unit.get("id"), material_index, "eboard")
        done = completion_key in completed_materials
        state = "done" if done else "open"
        token = _safe_widget_token(completion_key)
        with st.container(key=f"material_row_{state}_{token}"):
            with st.container(key=f"lesson_action_{state}_{token}"):
                st.link_button("▶ この教材をひらく", url, use_container_width=True)
            _render_done_action(completion_key, unit, completed_units, completed_materials, token)
        return

    for index, lesson in enumerate(lessons):
        number = int(lesson.get("order") or index + 1)
        title = str(lesson.get("title") or f"教材 {number}").strip()
        video_url = str(lesson.get("video_url") or "").strip()
        question_url = str(lesson.get("question_url") or "").strip()
        completion_key = _lesson_completion_key(unit.get("id"), material_index, number)
        done = completion_key in completed_materials
        state = "done" if done else "open"
        token = _safe_widget_token(completion_key)

        with st.container(key=f"material_row_{state}_{token}"):
            with st.container(key=f"lesson_action_{state}_{token}"):
                st.link_button(
                    f"▶ {number:02d}　{title}",
                    video_url,
                    use_container_width=True,
                )
            if question_url:
                problem_col, done_col = st.columns(2, gap="small")
                with problem_col:
                    with st.container(key=f"problem_action_{state}_{token}"):
                        st.link_button("✏️ もんだい", question_url, use_container_width=True)
                with done_col:
                    _render_done_action(completion_key, unit, completed_units, completed_materials, token)
            else:
                _render_done_action(completion_key, unit, completed_units, completed_materials, token)


def _render_standard_material(unit, material, material_index, completed_units, completed_materials):
    label = str(material.get("label") or "教材").strip()
    kind = str(material.get("kind") or "material").strip().lower()
    url = str(material.get("url") or "").strip()
    completion_key = _material_completion_key(unit.get("id"), material_index, kind)
    done = completion_key in completed_materials
    state = "done" if done else "open"
    token = _safe_widget_token(completion_key)

    with st.container(key=f"material_row_{state}_{token}"):
        if kind == "activity":
            instruction = html.escape(str(material.get("instruction") or "").strip())
            st.markdown(
                f'<div class="starter-card"><div class="starter-label">👐 まずは ためそう</div>{instruction}</div>',
                unsafe_allow_html=True,
            )
        elif kind == "youtube":
            with st.container(key=f"lesson_action_{state}_{token}"):
                st.link_button(f"▶ {label}", url, use_container_width=True)
            st.video(url)
        else:
            with st.container(key=f"lesson_action_{state}_{token}"):
                st.link_button(f"▶ {label}", url, use_container_width=True)
        _render_done_action(completion_key, unit, completed_units, completed_materials, token)


def material_buttons(unit, completed_units, completed_materials):
    """Show only the shortest study path. Every material has its own completion button."""
    materials = list((unit or {}).get("materials") or [])
    with st.container(key="study_materials"):
        for material_index, material in enumerate(materials):
            kind = str(material.get("kind") or "").strip().lower()
            if kind == "eboard":
                _render_eboard_material(unit, material, material_index, completed_units, completed_materials)
            else:
                _render_standard_material(unit, material, material_index, completed_units, completed_materials)


def render_ai_support(unit):
    """Show optional AI hints and image feedback without blocking the core curriculum."""
    with st.expander("🤖 AIせんせいに きく・しゃしんで みてもらう"):
        if get_client() is None:
            st.info("この機能を使うには、おうちの方がトップページの設定でAPIキーを登録します。教材を見る機能はそのまま使えます。")
            return

        question_tab, photo_tab = st.tabs(["ことばで きく", "しゃしんで みてもらう"])
        unit_token = _safe_widget_token(unit["id"])

        with question_tab:
            question = st.text_area(
                "わからないことを かいてね",
                placeholder="どうして こうなるの？",
                key=f"ai_question_{unit_token}",
                height=92,
            )
            if st.button("ヒントを もらう", use_container_width=True, key=f"ask_ai_{unit_token}"):
                if not question.strip():
                    st.warning("ききたいことを かいてね。")
                else:
                    try:
                        with st.spinner("かんがえています…"):
                            st.session_state[f"ai_answer_{unit_token}"] = ask_openai(question, unit)
                    except Exception as exc:
                        st.error(f"AIせんせいを呼べませんでした。おうちの方が設定を確認してください。（{exc}）")
            answer = st.session_state.get(f"ai_answer_{unit_token}")
            if answer:
                st.markdown(
                    '<div class="ai-answer">' + html.escape(str(answer)).replace("\n", "<br>") + "</div>",
                    unsafe_allow_html=True,
                )

        with photo_tab:
            uploaded = st.file_uploader(
                "もんだい・ノートの しゃしん",
                type=["jpg", "jpeg", "png", "webp"],
                key=f"answer_photo_{unit_token}",
            )
            if uploaded is not None:
                st.image(uploaded, caption="みてもらう しゃしん", use_container_width=True)
                if st.button("このしゃしんを みてもらう", use_container_width=True, key=f"check_photo_{unit_token}"):
                    try:
                        with st.spinner("ていねいに みています…"):
                            st.session_state[f"photo_answer_{unit_token}"] = ask_openai(
                                "まずヒントを一つください。",
                                unit,
                                image_bytes=uploaded.getvalue(),
                                image_mime=uploaded.type,
                            )
                    except Exception as exc:
                        st.error(f"しゃしんを確認できませんでした。おうちの方が設定を確認してください。（{exc}）")
            photo_answer = st.session_state.get(f"photo_answer_{unit_token}")
            if photo_answer:
                st.markdown(
                    '<div class="ai-answer">' + html.escape(str(photo_answer)).replace("\n", "<br>") + "</div>",
                    unsafe_allow_html=True,
                )

def grade_units(grade):
    return sorted([u for u in UNITS if u["grade"] == grade], key=lambda x: x["order"])


def completion_state():
    if "completed_units" not in st.session_state:
        st.session_state.completed_units = set()
    return st.session_state.completed_units


def material_completion_state():
    if "completed_materials" not in st.session_state:
        st.session_state.completed_materials = set()
    return st.session_state.completed_materials


def apply_requested_home_reset():
    """Clear transient study UI before any page widgets are rebuilt."""
    if not bool(st.session_state.get("_reset_to_home_requested")):
        return
    # Keep only learning progress and the parent-entered API key. Everything else is UI state.
    keep_keys = {"completed_units", "completed_materials", "openai_api_key", "home_grade_value"}
    for key in list(st.session_state.keys()):
        if key not in keep_keys:
            st.session_state.pop(key, None)


def render_home_reset_button(position):
    container_key = f"study_home_{position}"
    button_key = f"study_home_{position}_button"
    with st.container(key=container_key):
        if st.button("🏠 トップページに戻る", use_container_width=True, key=button_key):
            # Do the actual clearing at the start of the next run so widget-backed keys
            # are never mutated after their widgets were already instantiated.
            st.session_state["_reset_to_home_requested"] = True
            st.rerun()


def main():
    apply_requested_home_reset()
    inject_css()
    completed = completion_state()
    completed_materials = material_completion_state()

    selected_unit_id = str(st.session_state.get("selected_unit_id") or "").strip()
    selected_unit = next((u for u in UNITS if u["id"] == selected_unit_id), None)

    # ------------------------------------------------------------
    # HOME: children choose a grade, then tap a large unit button.
    # Keep explanations and parent-facing reference material off the main path.
    # ------------------------------------------------------------
    if selected_unit is None:
        st.markdown('<div class="main-title">🧮 さんすうナビ</div>', unsafe_allow_html=True)
        st.caption("5〜6歳の『はじめ』から、小学6年生まで。できた所から一歩ずつ進みます。")
        st.markdown('<div class="home-question">きょうは どれを やる？</div>', unsafe_allow_html=True)

        grade_options = list(COURSE_LABELS)
        saved_grade = st.session_state.get("home_grade_value")
        default_grade = int(saved_grade) if saved_grade is not None else 0
        if default_grade not in grade_options:
            default_grade = 0
        with st.container(key="home_grade"):
            grade = st.radio(
                "コース",
                grade_options,
                horizontal=True,
                index=grade_options.index(default_grade),
                format_func=lambda x: COURSE_LABELS[x],
                key="home_grade_radio",
            )
        st.session_state["home_grade_value"] = grade

        units = grade_units(grade)
        done_count = sum(1 for u in units if u["id"] in completed)
        next_unit = next((u for u in units if u["id"] not in completed), None)
        st.markdown(
            f'<div class="progress-line">できた　{done_count} / {len(units)}</div>',
            unsafe_allow_html=True,
        )
        st.progress(done_count / max(1, len(units)))
        if next_unit:
            st.markdown(
                f'<div class="next-unit">つぎの おすすめ　{next_unit["order"]:02d}　{html.escape(next_unit["title"])}</div>',
                unsafe_allow_html=True,
            )
        elif units:
            st.success("このコースは ぜんぶ できました！")

        with st.container(key="unit_picker_grid"):
            cols = st.columns(2)
            for index, unit in enumerate(units):
                status = "✓　" if unit["id"] in completed else ""
                label = f"{status}{unit['order']:02d}　{unit['title']}"
                with cols[index % 2]:
                    unit_state = "done" if unit["id"] in completed else "open"
                    with st.container(key=f"home_unit_{unit_state}_{_safe_widget_token(unit['id'])}"):
                        if st.button(
                            label,
                            use_container_width=True,
                            key=f"home_unit_{unit['id']}",
                        ):
                            st.session_state["selected_unit_id"] = unit["id"]
                            st.session_state["home_grade_value"] = grade
                            st.rerun()

        with st.expander("おうちの方へ"):
            st.caption("学習内容の基準・教材")
            st.write(
                "カリキュラムの骨格は文部科学省『小学校学習指導要領（平成29年告示）解説 算数編』に合わせています。"
                "教科書会社によって単元名・学習順は異なるため、アプリでは内容を学習しやすい単位に整理しています。"
            )
            st.write(
                "5〜6歳コースは学年の先取りを判定する試験ではありません。具体物を動かし、本人が言葉で説明できることを優先します。"
            )
            c1, c2, c3 = st.columns(3)
            with c1:
                st.link_button("文科省", MEXT_URL, use_container_width=True)
            with c2:
                st.link_button("算数編 PDF", MEXT_MATH_PDF, use_container_width=True)
            with c3:
                st.link_button("eboard", EBOARD_URL, use_container_width=True)

            st.divider()
            st.caption("AIせんせい（任意）")
            st.text_input(
                "OpenAI APIキー",
                type="password",
                key="openai_api_key",
                help="質問へのヒントと答案画像の確認にだけ使用します。未設定でも教材・進捗機能は使えます。",
            )
            st.caption("API利用料はChatGPT Workの利用枠とは別です。公開時は画面入力ではなく、アプリのSecrets設定を推奨します。")
        return

    # ------------------------------------------------------------
    # STUDY VIEW: details appear only after the child chooses a unit.
    # ------------------------------------------------------------
    unit = selected_unit
    grade = int(unit["grade"])
    units = grade_units(grade)
    course_chip = "5〜6歳" if grade == 0 else f"小学{grade}年"

    render_home_reset_button("top")

    st.markdown(
        f"""
        <div class="unit-card unit-card-compact">
          <div class="unit-title">{unit['order']:02d}. {unit['title']}</div>
          <span class="chip">{course_chip}</span><span class="chip">{DOMAIN_SHORT.get(unit['domain'], unit['domain'])}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Keep the child path direct: lesson -> matching problem -> done.
    migrate_legacy_unit_completion(unit, completed, completed_materials)
    sync_unit_completion(unit, completed, completed_materials)
    material_buttons(unit, completed, completed_materials)

    render_ai_support(unit)

    with st.expander("おうちの方へ：ねらいと見守り方"):
        st.markdown(f"**ねらい**　{unit['goal']}")
        st.markdown(f"**先にできるとよいこと**　{unit['prereq']}")
        st.markdown(f"**見守り方**　{unit['point']}")

    render_home_reset_button("bottom")


if __name__ == "__main__":
    main()
