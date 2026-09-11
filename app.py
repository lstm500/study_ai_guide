import base64
import os
import re
from html.parser import HTMLParser
from urllib.request import Request, urlopen

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
    page_title="算数ナビ AI先生",
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

        /* Study actions use the same radius and weight, avoiding oversized heavy controls. */
        .st-key-complete_action button {
            min-height: 50px !important;
            border-radius: 14px !important;
            font-weight: 750 !important;
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

    grade = unit["grade"]
    base_instructions = f"""
あなたは小学{grade}年生専任の算数教師です。
学習単元は「{unit['title']}」です。
到達目標は「{unit['goal']}」です。

ルール:
- 小学{grade}年生が理解できる日本語を使う。
- 1文を短くし、難しい専門用語を避ける。
- 正解だけを先に言わず、考え方を1段ずつ示す。
- 間違いを責めない。どこまでは合っているかを明確にする。
- 必要なら図の代わりに、●や□、数直線の簡単な文字表現を使う。
- 文章題では『分かっていること』『求めること』『式』を分ける。
- 学年外の高度な公式へ飛ばない。
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
        "eboard": "映像授業＋確認問題",
        "youtube": "解説動画",
        "web": "Web教材・プリント",
    }.get(kind, "教材")


def material_note(kind):
    return {
        "eboard": "この単元の主教材として使用します。短い映像授業と確認問題があります。",
        "youtube": "別の見せ方で理解を補う補助動画です。",
        "web": "図・プリント・補助解説として使います。",
    }.get(kind, "この単元の補助教材です。")


def material_buttons(unit):
    for idx, material in enumerate(unit["materials"]):
        st.markdown(f"**{idx + 1}. {material['label']}**")
        st.caption(f"{material_type_label(material['kind'])}｜{material_note(material['kind'])}")
        c1, c2 = st.columns([1.3, 4.7])
        with c1:
            st.link_button("教材を開く", material["url"], use_container_width=True)
        with c2:
            if idx == 0:
                st.caption("おすすめ順 1位：まずこの教材から始めます。")
        if material["kind"] == "youtube" and idx == 0:
            st.video(material["url"])
        if idx < len(unit["materials"]) - 1:
            st.divider()


def grade_units(grade):
    return sorted([u for u in UNITS if u["grade"] == grade], key=lambda x: x["order"])


def completion_state():
    if "completed_units" not in st.session_state:
        st.session_state.completed_units = set()
    return st.session_state.completed_units


def apply_requested_home_reset():
    """Clear transient study UI before any page widgets are rebuilt."""
    if not bool(st.session_state.get("_reset_to_home_requested")):
        return
    # Keep only learning progress and the parent-entered API key. Everything else is UI state.
    keep_keys = {"completed_units", "openai_api_key"}
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

    selected_unit_id = str(st.session_state.get("selected_unit_id") or "").strip()
    selected_unit = next((u for u in UNITS if u["id"] == selected_unit_id), None)

    # ------------------------------------------------------------
    # HOME: children choose a grade, then tap a large unit button.
    # Keep explanations and parent-facing reference material off the main path.
    # ------------------------------------------------------------
    if selected_unit is None:
        st.markdown('<div class="main-title">🧮 さんすうナビ</div>', unsafe_allow_html=True)
        st.markdown('<div class="home-question">きょうは どれを やる？</div>', unsafe_allow_html=True)

        default_grade = int(st.session_state.get("home_grade_value") or 1)
        if default_grade not in {1, 2, 3}:
            default_grade = 3
        with st.container(key="home_grade"):
            grade = st.radio(
                "がくねん",
                [1, 2, 3],
                horizontal=True,
                index=[1, 2, 3].index(default_grade),
                format_func=lambda x: f"小{x}",
                key="home_grade_radio",
            )
        st.session_state["home_grade_value"] = grade

        units = grade_units(grade)
        done_count = sum(1 for u in units if u["id"] in completed)
        st.markdown(
            f'<div class="progress-line">できた　{done_count} / {len(units)}</div>',
            unsafe_allow_html=True,
        )
        st.progress(done_count / max(1, len(units)))

        with st.container(key="unit_picker_grid"):
            cols = st.columns(2)
            for index, unit in enumerate(units):
                status = "✓　" if unit["id"] in completed else ""
                label = f"{status}{unit['order']:02d}　{unit['title']}"
                with cols[index % 2]:
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
            c1, c2, c3 = st.columns(3)
            with c1:
                st.link_button("文科省", MEXT_URL, use_container_width=True)
            with c2:
                st.link_button("算数編 PDF", MEXT_MATH_PDF, use_container_width=True)
            with c3:
                st.link_button("eboard", EBOARD_URL, use_container_width=True)
        return

    # ------------------------------------------------------------
    # STUDY VIEW: details appear only after the child chooses a unit.
    # ------------------------------------------------------------
    unit = selected_unit
    grade = int(unit["grade"])
    units = grade_units(grade)

    render_home_reset_button("top")

    st.markdown(
        f"""
        <div class="unit-card">
          <div class="unit-title">{unit['order']:02d}. {unit['title']}</div>
          <span class="chip">小学{unit['grade']}年</span><span class="chip">{DOMAIN_SHORT.get(unit['domain'], unit['domain'])}</span>
          <div class="goal-box"><b>ここまで できたら OK！</b><br>{unit['goal']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("💡 このたんげんのヒント"):
        st.write(unit["point"])
        st.caption(f"前にできているとよいこと：{unit['prereq']}")

    with st.container(key="complete_action"):
        if unit["id"] in completed:
            if st.button("✓ できた！　もう一度やる", use_container_width=True):
                completed.discard(unit["id"])
                st.rerun()
        else:
            if st.button("できた！ ✓", type="primary", use_container_width=True):
                completed.add(unit["id"])
                st.rerun()

    tab1, tab2, tab3, tab4 = st.tabs(["▶ みる", "💬 AI先生", "📚 教材＋AI", "📷 しゃしん"])

    with tab1:
        st.subheader("まず これを見よう")
        material_buttons(unit)
        st.divider()
        st.markdown("**れんしゅうする**")
        st.link_button(
            f"小学{grade}年の問題をひらく",
            OFFICIAL_PRACTICE[grade],
            use_container_width=True,
        )

    with tab2:
        st.subheader("AI先生に聞く")
        quick_col1, quick_col2, quick_col3 = st.columns(3)
        quick_prompt = None
        with quick_col1:
            if st.button("5分で教えて", use_container_width=True):
                quick_prompt = "この単元を、最初に学ぶ子向けに5分で読める長さで教えて。最後に確認問題を1問出して。"
        with quick_col2:
            if st.button("もっとやさしく", use_container_width=True):
                quick_prompt = "この単元を、具体物や身近な例を使って、とてもやさしく説明して。"
        with quick_col3:
            if st.button("問題を3もん", use_container_width=True):
                quick_prompt = "この単元の練習問題を、やさしい→標準の順に3問出して。答えは最初は隠して。"

        question = st.text_area("ききたいこと", placeholder="ここが わからない！", key=f"q_{unit['id']}")
        send = st.button("AI先生に聞く", type="primary", key=f"send_{unit['id']}")
        request_text = quick_prompt or (question.strip() if send else None)
        if request_text:
            try:
                with st.spinner("AI先生が考えています"):
                    answer = ask_openai(request_text, unit)
                st.markdown(answer)
            except Exception as exc:
                st.error(str(exc))
                st.info("APIキーがなくても『▶ みる』の教材は使えます。おうちの方が下の設定からAPIキーを入力するとAI機能が使えます。")

    with tab3:
        st.subheader("教材を見ながらAI先生に聞く")
        material_labels = [f"{i + 1}. {m['label']}" for i, m in enumerate(unit["materials"])]
        selected_material_label = st.selectbox(
            "教材",
            material_labels,
            key=f"material_select_{unit['id']}",
        )
        material_index = material_labels.index(selected_material_label)
        selected_material = unit["materials"][material_index]

        st.caption(f"{material_type_label(selected_material['kind'])}｜{material_note(selected_material['kind'])}")
        if selected_material["kind"] == "youtube":
            st.video(selected_material["url"])
        else:
            st.link_button("教材をひらく", selected_material["url"], use_container_width=True)

        context_key = f"source_context_{unit['id']}_{material_index}"
        label_key = f"source_label_{unit['id']}_{material_index}"

        if st.button("この教材をAI先生に読んでもらう", type="primary", key=f"load_material_{unit['id']}_{material_index}"):
            try:
                with st.spinner("教材を読み込んでいます"):
                    if selected_material["kind"] == "youtube":
                        video_id = extract_youtube_id(selected_material["url"])
                        if not video_id:
                            raise RuntimeError("登録されているYouTube URLを確認できませんでした。")
                        source_context = fetch_youtube_transcript(video_id)
                    else:
                        source_context = fetch_web_text(selected_material["url"])
                st.session_state[context_key] = source_context
                st.session_state[label_key] = selected_material["label"]
                st.success("読み込みました。下からAI先生に聞けます。")
            except Exception as exc:
                st.warning(f"教材本文・字幕の自動取得ができませんでした：{exc}")
                fallback = f"単元名: {unit['title']}\n学習目標: {unit['goal']}\n学習のポイント: {unit['point']}"
                st.session_state[context_key] = fallback
                st.session_state[label_key] = selected_material["label"] + "（単元情報を使用）"
                st.info("教材自体はそのまま使えます。AI先生は登録済みの単元情報を基準に説明します。")

        source_context = st.session_state.get(context_key, "")
        source_label = st.session_state.get(label_key, selected_material["label"])

        if source_context:
            q1, q2, q3 = st.columns(3)
            material_prompt = None
            with q1:
                if st.button("だいじな3つ", use_container_width=True, key=f"mp1_{unit['id']}_{material_index}"):
                    material_prompt = "この教材で大事なところを、小学生向けに3つだけ説明して。"
            with q2:
                if st.button("もっとやさしく", use_container_width=True, key=f"mp2_{unit['id']}_{material_index}"):
                    material_prompt = "この教材の内容を、具体物や簡単な例を使ってもっとやさしく説明して。"
            with q3:
                if st.button("問題を3もん", use_container_width=True, key=f"mp3_{unit['id']}_{material_index}"):
                    material_prompt = "この教材の内容から確認問題を3問出して。答えは最初は見せないで。"

            material_question = st.text_area(
                "教材でわからないところ",
                placeholder="ここを もう一ど おしえて！",
                key=f"material_q_{unit['id']}_{material_index}",
            )
            ask_material = st.button("AI先生に聞く", key=f"material_send_{unit['id']}_{material_index}")
            request_text = material_prompt or (material_question.strip() if ask_material else None)
            if request_text:
                try:
                    with st.spinner("教材の内容に沿って説明しています"):
                        answer = ask_openai(
                            request_text,
                            unit,
                            source_context=source_context,
                            source_label=source_label,
                        )
                    st.markdown(answer)
                except Exception as exc:
                    st.error(str(exc))
        else:
            st.info("先に『この教材をAI先生に読んでもらう』を押してください。")

    with tab4:
        st.subheader("ノートや答案を見てもらう")
        uploaded = st.file_uploader(
            "しゃしんを えらぶ",
            type=["png", "jpg", "jpeg", "webp"],
            key=f"upload_{unit['id']}",
        )
        if uploaded is not None:
            st.image(uploaded, caption="この写真を見てもらいます", use_container_width=True)
            extra = st.text_input("ひとこと（なくてもOK）", placeholder="ヒントだけほしい", key=f"extra_{unit['id']}")
            if st.button("AI先生に見てもらう", type="primary", key=f"grade_{unit['id']}"):
                try:
                    image_bytes = uploaded.getvalue()
                    with st.spinner("答案を確認しています"):
                        answer = ask_openai(
                            extra or "この答案を学年に合う言葉で添削して。",
                            unit,
                            image_bytes=image_bytes,
                            image_mime=uploaded.type,
                        )
                    st.markdown(answer)
                except Exception as exc:
                    st.error(str(exc))

    st.divider()
    with st.expander("おうちの方へ・AI設定"):
        st.write("OpenAI APIキーを設定すると、AI先生・教材への質問・答案添削が使えます。")
        st.text_input("OpenAI API Key", type="password", key="openai_api_key")
        st.caption("この試作版はAI処理に gpt-5.6-luna を使用します。")

    render_home_reset_button("bottom")


if __name__ == "__main__":
    main()
