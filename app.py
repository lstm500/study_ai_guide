import base64
import os
import re
from urllib.parse import quote_plus

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
            {"kind": "youtube", "label": "福岡市教育委員会：小1算数 かたちづくり①", "url": "https://www.youtube.com/watch?v=PXB4zGO0SRQ"},
        ],
    },
    {
        "id": "g1-10", "grade": 1, "order": 10, "domain": "C 測定",
        "title": "長さ・広さ・かさをくらべる",
        "goal": "長さ・広さ・かさを、直接比べたり同じ基準を使ったりして比較する。",
        "point": "比べるときは『端をそろえる』『同じ大きさのものを基準にする』という公平な比較が中心です。",
        "prereq": "数を数える",
        "materials": [
            {"kind": "youtube", "label": "福岡市教育委員会：小1算数 どちらがながい①", "url": "https://www.youtube.com/watch?v=DF19GXKvBB0"},
            {"kind": "web", "label": "ロイロノート授業案：小1算数 おおきさくらべ等", "url": "https://help.loilonote.app/%E5%B0%8F%E5%AD%A6%EF%BC%91%E5%B9%B4%E7%AE%97%E6%95%B0"},
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
            {"kind": "web", "label": "ロイロノート授業案：かずしらべ", "url": "https://help.loilonote.app/--66ab077761be35001d279a8e"},
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
            {"kind": "youtube", "label": "オンライン授業ちゃんねる：ひょうとグラフ", "url": "https://www.youtube.com/watch?v=yhxIhingzZY"},
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
        .block-container {padding-top: 1.2rem; padding-bottom: 3rem; max-width: 1100px;}
        .main-title {font-size: 2.1rem; font-weight: 800; line-height: 1.2; margin-bottom: .25rem;}
        .subtle {color: #6b7280; font-size: .93rem;}
        .unit-card {border: 1px solid rgba(120,120,120,.22); border-radius: 18px; padding: 18px 20px; margin: 10px 0 14px 0;}
        .unit-title {font-size: 1.35rem; font-weight: 800; margin-bottom: .2rem;}
        .chip {display:inline-block; border:1px solid rgba(120,120,120,.35); border-radius:999px; padding:3px 9px; font-size:.8rem; margin-right:6px;}
        .goal-box {border-radius:14px; padding:14px 16px; background:rgba(120,120,120,.07); margin-top:10px;}
        .tiny {font-size:.82rem; color:#6b7280;}
        div[data-testid="stMetricValue"] {font-size:1.35rem;}
        @media (max-width: 700px) {
            .main-title {font-size: 1.65rem;}
            .unit-card {padding: 14px 14px;}
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


def ask_openai(text, unit, transcript=None, image_bytes=None, image_mime=None):
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

    if transcript:
        base_instructions += "\n- 動画について答えるときは、下の字幕内容を優先し、字幕にない内容を動画内の発言として作らない。"
        text = f"""動画字幕:\n{transcript[:22000]}\n\n子どもの質問:\n{text}"""

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


def material_buttons(unit):
    for idx, material in enumerate(unit["materials"]):
        col1, col2 = st.columns([5, 1.4])
        with col1:
            icon = "▶" if material["kind"] == "youtube" else "教材"
            st.markdown(f"**{icon} {material['label']}**")
        with col2:
            st.link_button("開く", material["url"], use_container_width=True)
        if material["kind"] == "youtube" and idx == 0:
            st.video(material["url"])


def grade_units(grade):
    return sorted([u for u in UNITS if u["grade"] == grade], key=lambda x: x["order"])


def completion_state():
    if "completed_units" not in st.session_state:
        st.session_state.completed_units = set()
    return st.session_state.completed_units


def main():
    inject_css()
    completed = completion_state()

    st.markdown('<div class="main-title">算数ナビ AI先生</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subtle">文部科学省の学習指導要領を骨格に、小学1〜3年の算数を単元ごとに学ぶ試作版です。</div>',
        unsafe_allow_html=True,
    )

    top1, top2, top3 = st.columns([1.2, 1.2, 2.6])
    with top1:
        grade = st.radio("学年", [1, 2, 3], horizontal=True, format_func=lambda x: f"小{x}")
    units = grade_units(grade)
    done_count = sum(1 for u in units if u["id"] in completed)
    with top2:
        st.metric("学習済み", f"{done_count}/{len(units)}")
    with top3:
        st.markdown("**この学年の進み具合**")
        st.progress(done_count / max(1, len(units)))

    with st.expander("このアプリの基準資料・教材について"):
        st.write("カリキュラムの骨格は文部科学省『小学校学習指導要領（平成29年告示）解説 算数編』に合わせています。教科書会社によって単元名・学習順は異なるため、アプリでは内容を学習しやすい単位に整理しています。")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.link_button("文科省 解説ページ", MEXT_URL, use_container_width=True)
        with c2:
            st.link_button("算数編 PDF", MEXT_MATH_PDF, use_container_width=True)
        with c3:
            st.link_button("eboard 算数一覧", EBOARD_URL, use_container_width=True)

    labels = []
    label_to_unit = {}
    for u in units:
        mark = "✓" if u["id"] in completed else "○"
        label = f"{mark} {u['order']:02d}. {u['title']}  ｜ {DOMAIN_SHORT.get(u['domain'], u['domain'])}"
        labels.append(label)
        label_to_unit[label] = u

    selected_label = st.selectbox("学ぶ単元を選ぶ", labels)
    unit = label_to_unit[selected_label]

    st.markdown(
        f"""
        <div class="unit-card">
          <div class="unit-title">{unit['order']:02d}. {unit['title']}</div>
          <span class="chip">小学{unit['grade']}年</span><span class="chip">{unit['domain']}</span>
          <div class="goal-box"><b>できるようになること</b><br>{unit['goal']}</div>
          <p><b>学習のポイント</b><br>{unit['point']}</p>
          <p class="tiny"><b>前にできているとよいこと：</b>{unit['prereq']}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns([1, 3])
    with c1:
        if unit["id"] in completed:
            if st.button("学習済みを取り消す", use_container_width=True):
                completed.discard(unit["id"])
                st.rerun()
        else:
            if st.button("この単元を学習済みにする", type="primary", use_container_width=True):
                completed.add(unit["id"])
                st.rerun()
    with c2:
        incomplete = [u for u in units if u["id"] not in completed]
        if incomplete:
            st.caption(f"次の未学習単元：{incomplete[0]['title']}")
        else:
            st.caption("この学年の登録単元はすべて学習済みです。")

    tab1, tab2, tab3, tab4 = st.tabs(["動画・教材", "AI先生", "YouTubeを読み込む", "答案を添削"])

    with tab1:
        st.subheader("この単元の教材")
        material_buttons(unit)
        query = quote_plus(f"小学{grade}年 算数 {unit['title']} 解説")
        st.link_button("YouTubeで別の解説も探す", f"https://www.youtube.com/results?search_query={query}")
        st.caption("外部教材は公開状況や内容が変わることがあります。保護者が内容を確認して利用してください。")

    with tab2:
        st.subheader("AI先生に聞く")
        st.write("この単元の目標と学年を前提に、説明の難しさを調整します。")
        quick_col1, quick_col2, quick_col3 = st.columns(3)
        quick_prompt = None
        with quick_col1:
            if st.button("5分で教えて", use_container_width=True):
                quick_prompt = "この単元を、最初に学ぶ子向けに5分で読める長さで教えて。最後に確認問題を1問出して。"
        with quick_col2:
            if st.button("もっとやさしく", use_container_width=True):
                quick_prompt = "この単元を、具体物や身近な例を使って、とてもやさしく説明して。"
        with quick_col3:
            if st.button("練習問題を3問", use_container_width=True):
                quick_prompt = "この単元の練習問題を、やさしい→標準の順に3問出して。答えは最初は隠して。"

        question = st.text_area("質問を書く", placeholder="例：8+7で、どうして10を先につくるの？", key=f"q_{unit['id']}")
        send = st.button("AI先生に聞く", type="primary", key=f"send_{unit['id']}")
        request_text = quick_prompt or (question.strip() if send else None)
        if request_text:
            try:
                with st.spinner("AI先生が考えています"):
                    answer = ask_openai(request_text, unit)
                st.markdown(answer)
            except Exception as exc:
                st.error(str(exc))
                st.info("APIキーがなくても、上の『動画・教材』は利用できます。下の設定からAPIキーを入力するとAI機能が使えます。")

    with tab3:
        st.subheader("好きなYouTube動画をAI先生と見る")
        st.write("YouTube URLを貼ると動画を表示し、字幕を取得できた場合は、その字幕を根拠にAIへ質問できます。")
        yt_url = st.text_input("YouTube URL", key=f"yt_{unit['id']}", placeholder="https://www.youtube.com/watch?v=...")
        video_id = extract_youtube_id(yt_url)
        if yt_url:
            if video_id:
                st.video(yt_url)
            else:
                st.warning("YouTube動画URLを確認してください。")

        transcript_key = f"transcript_{unit['id']}"
        if video_id and st.button("字幕を読み込む", key=f"loadtr_{unit['id']}"):
            try:
                with st.spinner("字幕を読み込んでいます"):
                    transcript = fetch_youtube_transcript(video_id)
                st.session_state[transcript_key] = transcript
                st.success(f"字幕を読み込みました（{len(transcript):,}文字）。")
            except Exception as exc:
                st.error(str(exc))

        transcript = st.session_state.get(transcript_key, "")
        with st.expander("字幕を手動で貼る / 読み込んだ字幕を見る"):
            manual = st.text_area("字幕・文字起こし", value=transcript, height=180, key=f"manualtr_{unit['id']}")
            if manual != transcript:
                st.session_state[transcript_key] = manual
                transcript = manual

        video_question = st.text_area(
            "動画について質問",
            placeholder="例：この動画の3つのポイントを教えて。2:30あたりの考え方をやさしく説明して。",
            key=f"vquestion_{unit['id']}",
        )
        if st.button("動画AI先生に聞く", type="primary", key=f"vsend_{unit['id']}"):
            if not transcript.strip():
                st.warning("先に字幕を読み込むか、字幕・文字起こしを貼ってください。")
            elif not video_question.strip():
                st.warning("質問を書いてください。")
            else:
                try:
                    with st.spinner("動画の内容を確認しています"):
                        answer = ask_openai(video_question.strip(), unit, transcript=transcript)
                    st.markdown(answer)
                except Exception as exc:
                    st.error(str(exc))

    with tab4:
        st.subheader("答案写真をAI添削")
        st.write("問題用紙やノートの写真をアップロードすると、この単元の学年に合わせて考え方を説明します。")
        uploaded = st.file_uploader(
            "答案の写真",
            type=["png", "jpg", "jpeg", "webp"],
            key=f"upload_{unit['id']}",
        )
        if uploaded is not None:
            st.image(uploaded, caption="添削する画像", use_container_width=True)
            extra = st.text_input("補足（任意）", placeholder="例：答えをすぐ言わずヒントだけほしい", key=f"extra_{unit['id']}")
            if st.button("この答案を添削する", type="primary", key=f"grade_{unit['id']}"):
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
    with st.expander("AI機能の設定"):
        st.write("OpenAI APIキーを設定すると、AI先生・動画字幕への質問・答案添削が使えます。キーはこのブラウザの現在のセッション内だけで使用します。Streamlit CloudではSecretsに `OPENAI_API_KEY` を設定する方法も使えます。")
        st.text_input("OpenAI API Key", type="password", key="openai_api_key")
        st.caption("この試作版はAI処理に gpt-5.6-luna を使用します。")


if __name__ == "__main__":
    main()
