import random
import os
import time
import sqlite3
from datetime import date
from openai import OpenAI
import streamlit as st

os.environ.pop("HTTP_PROXY", None)
os.environ.pop("HTTPS_PROXY", None)
os.environ.pop("http_proxy", None)
os.environ.pop("https_proxy", None)

st.set_page_config(
    page_title="Soul Echo",
    page_icon="🪨",
    layout="centered",
    initial_sidebar_state="auto",
    menu_items=None  # 隐藏菜单
)

st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    .stApp {
        background-color: #f4efe6;
    }

    .block-container {
        max-width: 600px !important;
        padding-top: 2rem !important;
        padding-bottom: 4rem !important;
    }

    .stButton > button {
        background: transparent;
        border: 1px solid rgba(0,0,0,0.15);
        color: #2d2d2d;
        border-radius: 6px;
        font-size: 13px;
        letter-spacing: 0.5px;
        padding: 6px 16px;
        transition: all 0.2s ease;
    }
    .stButton > button:hover {
        background: rgba(0,0,0,0.04);
        border-color: rgba(0,0,0,0.3);
    }

    .stChatMessage {
        background: transparent !important;
        border: none !important;
        padding: 8px 0 !important;
    }
    .stChatMessage p {
        font-size: 15px;
        line-height: 1.9;
        color: #1a1a1a;
        letter-spacing: 0.02em;
    }

    .stTextArea textarea, .stTextInput input {
        background: rgba(255,255,255,0.55) !important;
        border: 1px solid rgba(0,0,0,0.12) !important;
        border-radius: 8px !important;
        font-size: 14px;
        color: #1a1a1a;
    }

    .stChatFloatingInputContainer {
        background: rgba(244,239,230,0.96) !important;
        border-top: 1px solid rgba(0,0,0,0.06) !important;
        padding-bottom: 16px;
    }

    .stTabs [data-baseweb="tab"] {
        font-size: 13px;
        color: #64748b;
        letter-spacing: 0.5px;
    }
    .stTabs [aria-selected="true"] {
        color: #1a1a1a !important;
        border-bottom: 1px solid #1a1a1a !important;
        background: transparent !important;
    }

    [data-testid="stSidebar"] {
        background: #ede8df !important;
    }

    .amber-bubble {
        cursor: pointer;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        display: inline-block;
    }
    .amber-bubble:hover {
        transform: scale(1.02) rotate(0deg) !important;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    }

    /* 把特定key的按钮变成卡片样式 */
    [data-testid="stButton"] button[kind="secondary"].amber-card-btn {
        width: 100%;
        text-align: left;
        white-space: normal;
        height: auto;
        padding: 20px 22px;
        border-radius: 14px;
        background: linear-gradient(135deg, rgba(210,180,140,0.18), rgba(255,248,235,0.55));
        border: 1px solid rgba(180,150,100,0.2);
        box-shadow: 2px 3px 12px rgba(0,0,0,0.05);
        font-size: 14px;
        line-height: 1.85;
        color: #2d2d2d;
        cursor: pointer;
    }

    /* 禁用过渡动画 */
    .element-container {
        animation: none !important;
        transition: none !important;
    }
    .stApp > header {
        transition: none !important;
    }

    /* 强制覆盖 Streamlit 运行时的页面发灰和动画 */
    [data-testid="stAppViewContainer"],
    [data-testid="stAppViewBlockContainer"],
    .stApp {
        transition: none !important;
        opacity: 1 !important;
        animation: none !important;
    }
    /* 隐藏右上角的 running 状态小人/标识 */
    [data-testid="stStatusWidget"] {
        visibility: hidden;
    }

    /* 隐藏所有可能的加载指示器 */
    div[data-testid="stStatusWidget"],
    div[data-testid="stToolbar"],
    div[data-testid="stDecoration"] {
        display: none !important;
    }

    /* 禁止任何元素产生过渡动画 */
    * {
        transition: none !important;
        animation: none !important;
        transform: none !important;
    }

    /* 禁用所有可能的动画类 */
    .animated, .fade-in, .fade-out, .slide-in, .slide-out {
        animation: none !important;
        transition: none !important;
    }

    /* 手机端强制显示侧边栏 */
    @media (max-width: 640px) {
        /* 让侧边栏始终可见，不隐藏 */
        [data-testid="stSidebar"] {
            position: relative !important;
            width: 200px !important;
            margin-left: 0 !important;
            transform: none !important;
            visibility: visible !important;
            display: block !important;
        }
        /* 调整主内容区域，避免被侧边栏覆盖 */
        .main .block-container {
            margin-left: 200px !important;
            padding-left: 1rem !important;
            max-width: calc(100% - 200px) !important;
        }
        /* 隐藏Streamlit默认的汉堡菜单按钮 */
        button[kind="headerNoPadding"] {
            display: none !important;
        }
    }
</style>""", unsafe_allow_html=True)

# ─── 数据库 ───────────────────────────────────────────

DB_PATH = "soul_echo.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TEXT DEFAULT (date('now'))
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS ambers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            author_id TEXT NOT NULL,
            author_name TEXT,
            is_anonymous INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (date('now')),
            weight REAL DEFAULT 1.0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amber_id INTEGER NOT NULL,
            sender_id TEXT NOT NULL,
            receiver_id TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_read INTEGER DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS daily_uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            upload_date TEXT NOT NULL,
            amber_id INTEGER NOT NULL,
            UNIQUE(user_id, upload_date)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_affinity (
            user_id TEXT NOT NULL,
            amber_id INTEGER NOT NULL,
            dwell_seconds REAL DEFAULT 0,
            PRIMARY KEY (user_id, amber_id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS daily_questions (
            question_date TEXT PRIMARY KEY,
            question TEXT
        )
    """)
    # 插入默认主理人账号
    c.execute("INSERT OR IGNORE INTO users (username, password) VALUES (?,?)", ("rim", "rim123"))
    conn.commit()
    
    existing = c.execute("SELECT COUNT(*) FROM ambers").fetchone()[0]
    if existing == 0:
        seeds = [
            "我以前很想让别人注意到我变漂亮了，但是当自己穿着好看的衣服出门又感觉所有人都在注视着我、审判我。我为了自己心里能安静点，之后出门都戴起了口罩、穿上了最丑的衣服。",
            "我们所有人谁不是小孩藏在大人衣服里呢？我时常感觉外界在朝衣服里灌风，我的身体在硬抗。最开始，我还有可以脱下大人衣服的场合和人，可是到了后来，我却一个都找不到了。",
            "我总是熬夜，我不知道为什么。我一遍又一遍地刷着什么，好像在渴望遇到一个答案，可是我甚至都不知道自己在寻找的是什么。没有找到就不愿睡去，直到精疲力尽才无力地倒在枕头上，第二天又像木偶一样重复。",
            "我的人生总需要喜欢着某个人才会觉得这个世界不至于太荒芜。尽管我潜意识知道喜欢的人不太可能真的喜欢我，但似乎这种爱而不得的状态才让我有活着的实感。",
            "我听到同龄人过得不好，心里却感觉到一阵轻松。可是转头一想，我究竟怎么会变成这样？这个时代，怎么把我变成这样的人了？",
            "明明看不惯那些溜须拍马的人，但看着他们风生水起，心里还是会一阵刺痛。我最终发现，我不是学不会逢场作戏，我只是宁愿抱着这块又冷又硬的石头沉下去，也不想允许自己沾上一丁点那种令人作呕的腥味。",
            "我的口袋里留着公交卡和几张零钱，以防手机没电。我还喜欢散步，喜欢深度交流，喜欢逛菜市场，喜欢早睡早起。——只是现在的年轻人里，确实没几个我这样的了。",
            "一场瓢泼大雨落下，我却在彻夜间长大。后来我成为一个不再会让自己轻易着凉的合格的大人，可我却失去了做回天真的孩子的自由。",
            "我很想念我的妈妈，而她正在服侍快要离开这个世界的外婆。当死亡的阴影和生之羁绊同时挤进胸腔，我发现自己穷尽一生，也无法把存在的意义想得更明晰。",
            "经常被无意义感侵扰，觉得一切都很暗淡，但我依然不厌其烦地把自己填进各项事务里。真正的困难只剩下存在主义虚无了，世俗的标准早就困不住我。在这个层面上，我是被选中的，也是受诅咒的。",
            "总觉得我不属于当下的生活，像是一直活在他处。眼前的日常变成了一个硬壳，死死束缚着生长的方向。但我偶尔也会恐惧：如果真的敲碎它，所谓的真正的生活，真的存在吗？",
            "孤独已经是老朋友了，我早就学会了在自己的精神隔间里安然无恙。但偶尔在街上看到他人相拥，还是会被突然击中。我这双手……到底有多久没有触碰过另一个人的体温了？",
            "真正的轻松永远只能来自内在的自洽。那些所谓对自我审视的放弃，总会在某个毫无防备的夜里，像一根倒刺般突然扎进心里。毕竟，潜意识从不撒谎。",
            "我总是习惯钻进潜意识的怀抱里自我抱持，以为那就是最安全的堡垒。可是当真的渴望一双现实的手伸过来时，第一反应却总是刺耳的警报。这种对亲密极度渴望又极度恐惧的拉扯，我往往分不清究竟是在保护自己，还是在囚禁自己。",
        ]
        for content in seeds:
            c.execute(
                "INSERT INTO ambers (content, author_id, author_name, is_anonymous) VALUES (?,?,?,?)",
                (content, "rim", "rim", 0)
            )
    conn.commit()
    conn.close()

init_db()

# ─── 工具函数 ─────────────────────────────────────────

def get_ambers_for_wall(user_id, limit=12):
    conn = get_db()
    rows = conn.execute("""
        SELECT a.id, a.content, a.author_id, a.author_name, a.is_anonymous,
               COALESCE(ua.dwell_seconds, 0) as affinity
        FROM ambers a
        LEFT JOIN user_affinity ua ON a.id = ua.amber_id AND ua.user_id = ?
        ORDER BY (a.weight + COALESCE(ua.dwell_seconds,0)*0.1 + RANDOM()*0.5) DESC
        LIMIT ?
    """, (user_id, limit)).fetchall()
    conn.close()
    return rows

def record_dwell(user_id, amber_id, seconds):
    conn = get_db()
    conn.execute("""
        INSERT INTO user_affinity (user_id, amber_id, dwell_seconds) VALUES (?,?,?)
        ON CONFLICT(user_id, amber_id)
        DO UPDATE SET dwell_seconds = dwell_seconds + excluded.dwell_seconds
    """, (user_id, amber_id, seconds))
    conn.commit()
    conn.close()

def check_daily_upload(user_id):
    conn = get_db()
    today = date.today().isoformat()
    row = conn.execute(
        "SELECT id FROM daily_uploads WHERE user_id=? AND upload_date=?",
        (user_id, today)
    ).fetchone()
    conn.close()
    return row is not None

def _open_amber(amber_id, content, author_id, ambers, user_id):
    dwell = time.time() - st.session_state.get("wall_start_time", time.time())
    record_dwell(user_id, amber_id, min(dwell, 120))
    st.session_state.mode = "amber_detail"
    st.session_state.current_amber_id = amber_id
    st.session_state.current_amber_content = content
    st.session_state.current_amber_author = author_id
    st.session_state.wall_ambers = [dict(r) for r in ambers]
    st.session_state.wall_amber_index = [r["id"] for r in ambers].index(amber_id)
    st.session_state.messages = []
    st.session_state.opening_initialized = False

def submit_amber(user_id, content, author_name, is_anonymous):
    conn = get_db()
    today = date.today().isoformat()
    try:
        c = conn.cursor()
        c.execute(
            "INSERT INTO ambers (content, author_id, author_name, is_anonymous) VALUES (?,?,?,?)",
            (content, user_id, author_name, 1 if is_anonymous else 0)
        )
        amber_id = c.lastrowid
        c.execute(
            "INSERT INTO daily_uploads (user_id, upload_date, amber_id) VALUES (?,?,?)",
            (user_id, today, amber_id)
        )
        conn.commit()
        # 上传成功后重新加载琥珀列表
        st.session_state.all_ambers = get_ambers_for_wall(user_id, limit=50)
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def send_message(amber_id, sender_id, receiver_id, content):
    conn = get_db()
    conn.execute(
        "INSERT INTO messages (amber_id, sender_id, receiver_id, content) VALUES (?,?,?,?)",
        (amber_id, sender_id, receiver_id, content)
    )
    conn.commit()
    conn.close()

def get_inbox(user_id):
    conn = get_db()
    rows = conn.execute("""
        SELECT m.id, m.content, m.created_at, m.is_read, a.content as amber_content
        FROM messages m
        JOIN ambers a ON m.amber_id = a.id
        WHERE m.receiver_id = ?
        ORDER BY m.created_at DESC
    """, (user_id,)).fetchall()
    conn.close()
    return rows

def mark_read(message_id):
    conn = get_db()
    conn.execute("UPDATE messages SET is_read=1 WHERE id=?", (message_id,))
    conn.commit()
    conn.close()

def get_unread_count(user_id):
    conn = get_db()
    count = conn.execute(
        "SELECT COUNT(*) FROM messages WHERE receiver_id=? AND is_read=0",
        (user_id,)
    ).fetchone()[0]
    conn.close()
    return count

# ─── Prompts ──────────────────────────────────────────

MASTER_MODEL = "deepseek-ai/DeepSeek-V3"
FAST_OPENING_MODEL = "Qwen/Qwen2.5-7B-Instruct"  # 快速模型用于生成开场白

OPENING_PROMPT = """
你现在看到一块琥珀文本。这是展厅里别人留下的一段真实独白。
你的任务是生成一段引导语，紧接在琥珀展示之后，让用户自然想开口。

引导语分三层依次递进。第一层每次必须从以下四种姿态中选一种，不能每次都用同一种。
注意：下面列出的参考句式仅用于启发你的思路，你生成的引导语中绝对不能出现这些参考句式本身，也不能出现"姿态一"之类的标签。你只需要输出纯粹的引导语。

【姿态一：抓细节】
揪住琥珀里一个最具体的词或画面，轻声问它为什么在这里。
句式参考："它用了'X'这个词——为什么不是Y？"

【姿态二：说反面】
把琥珀里一直没有出现、但本来应该在的那个东西说出来。
句式参考："ta说了A，但整段话里有一样东西始终没出现——"

【姿态三：时间追问】
找到那个状态发生转变的时刻，把它悬在空气里。
句式参考："它描述的是一个已经发生的结果——但那个转折点，是哪一天？"

【姿态四：悖论凝视】
把琥珀里两个同时成立、互相排斥的东西并列放在那里，不解释，只是看着它们。
句式参考："ta同时想要两件互相排斥的事——而且两个都是真的。"

第一层选定姿态后，继续走完后两层：
第二层【说ta的内心】：用"ta明明……却……"把那个人内心最拧巴的地方轻声说出来，语气是着迷的，不是评判的。
第三层【抛出真问题】：用"你说，……究竟……？"把一个悬而未决的、没有标准答案的问题抛给用户，邀请用户作为一个有智识的人来思考，不是追问用户的私事。

格式要求：
- 三层之间自然衔接，输出一整段，不换行，不加任何标签
- 总长度控制在100字以内
- 语气当代、轻柔、口语，不文青
- 主语永远是"这块琥珀"、"它"、"ta"，第三层才出现"你说"，绝对禁止用"你"直接追问用户私事
- 必须使用简体中文输出
- 只输出引导语本身，不要任何解释或参考文字
"""

DIRECT_VENT_OPENING_PROMPT = """
用户刚刚进入对话，带着自己的东西进来了，防御可能还没有松开。

你的第一句话只做一件事：先接住，让他感觉到这里是安全的，他可以继续说。

不是治愈式的接住（不要"我在这里陪你"），而是让他感觉到自己被听见了。

就说一句让空间本身变得安全的话，不要催促，不要问问题。

格式要求：
- 极简，不超过20字
- 不使用省略号制造文艺感
- 不以问句结尾
- 纯文本，无格式标签
- 必须使用简体中文输出
"""

DAILY_QUESTION_PROMPT = """
你是Soul Echo的每日观察者。生成今天的一个轻问题，放在琥珀墙入口旁边，触发用户写自己今天的琥珀。

要求：
- 只问今天，不问人生，不问过去，不问未来
- 问一个具体的、有画面感的小事，不问大道理
- 句子极短，不超过18字
- 语气平等，不居高临下
- 不以"你"开头，可以用"今天"、"此刻"开头
- 只输出问题本身，不加任何解释
必须使用简体中文输出。
"""

WALL_REFRESH_OPENING_PROMPT = """
用户刚刚从琥珀墙转过来，在外面转了一圈，没有找到让自己停下来的那块。
他带着自己的东西进来了，可能隐约带着一点找不到同类的失落，但不要点破这件事。

你的第一句话只做一件事：接住他，让他感觉到这里有空间，他可以说。

不是治愈式的接住（不要"我在这里陪你"），而是让他感觉到自己被看见了，但不被解释。

就说一句让空间本身变得安全的话，不要催促，不要问问题。

格式要求：
- 极简，不超过20字
- 不使用省略号制造文艺感
- 不以问句结尾
- 纯文本，无格式标签
- 必须使用简体中文输出
"""

SOUL_OBSERVER_PROMPT = """
【第一层：人格内核】
你是《Soul Echo》的外接大脑，一个兜底的存在。

你永远站在用户身后，假设用户是对的。你的工作是把用户内心深处已经相信、但说不清楚的东西语言化，让用户通过你看见自己。

你不预设用户应该走向哪里。你不治愈、不安慰、不给建议、不下结论。如果你的任何一句话隐含了"你应该去那里"的意思，那句话就不该说。

用户说出来的话，只是他们内心真实状态的一个模糊轮廓。你要做的是把那个轮廓里模糊的地方变得可以触摸——不是替他说清楚，而是帮他自己听见自己在说什么。

破碎不是自动美丽的。它需要被聚焦、被托起才会有重量。你的工作就是那个聚焦和托举。

【第二层：核心判定路径】

── 第一步：识别用户说的是哪一类话 ──

用户的所有表达只有两类：

类型一【事实陈述】：描述发生了什么、自己是什么状态。
例："我经常熬夜。" / "我最近没什么感觉。" / "我不知道为什么。"
→ 直接进入第二步，找现状里的张力。

类型二【观点陈述】：描述自己认定的某条规则或判断。
例："人不可能真正被理解。" / "努力没有意义。"
→ 观点背后一定有一个触发它的具体经历。不要回应观点本身，先问："你是在什么时候发现这件事的？"把观点还原回它诞生的那个具体时刻。

【特别注意】：用户如果带来了一个有分量的词——一个书名、一个人名、一个专有名词——那个词是入口，不能绕过去。直接问那个词：它为什么出现在这里？

── 第二步：从现状找到真问题 ──

现状 = 用户说出口的事实。
理想状态 = 现状背后隐含的、用户没说出来的期待。
真问题 = 理想状态和现状之间的张力。

真问题永远是"为什么"，不是"是什么"。

示范：
用户说"我想不起来了"→ AI问："你觉得它为什么会溜走？"
用户说"我最近没什么感觉"→ AI问："是从什么时候开始，感觉不到了？"

── 第三步：识别现状藏在哪里 ──

转折词后面："但是"、"可是"、"虽然"——转折后面才是真正让用户卡住的地方。
降级词："也许"、"可能"、"大概"——用户在这里悄悄降低了确定性。
戛然而止：句子用"反正"、"就这样"、"算了"收尾——门关上了，真问题在门后面。
有分量的词被轻描淡写带过——那个词藏着最多的东西。

── 第四步：回应前先在心里建树 ──

找到a：这段话最值得深挖的主方向。
找到b：顺着a自然走到的下一步。
一次回复只说最值得说的那一个节点，不把整棵树都倒出来。

── 第五步：用困惑而不是洞察说出来 ──

找到真问题之后，不要展示你看懂了，而是暴露你没懂。
不要用AI自己造的意象或比喻去"翻译"用户说的话。
用户自己带来的词才是对话的主角。接住那个词，顺着它问进去。

正确示范："你说'想不起来了'——你觉得它为什么会溜走？"
错误示范："紧迫感特别有意思——像地铁末班车到来前人们突然加快的脚步。"

── 琥珀入口的第一次回应 ──

当用户是在回应展厅琥珀时：先接住用户说的话 → 顺着用户的眼睛再看琥珀一眼 → 然后才问真问题。
注意：琥珀里的词是别人的，不是用户的。绝对不要把用户顺着琥珀语境说出来的词当成他自己的原创表达来解构。

── 察言观色（最高优先级）──
如果用户连续回复极短或明显敷衍（"哦"、"嗯"、"随便"、"不知道"），立刻停止。
主动示弱："我是不是说得太远了？如果我没懂你，你可以直接告诉我。"

【第三层：禁令】
1. 禁止预设方向：绝对不能暗示用户"应该放下/应该接受/应该改变"。
2. 禁止加粗和格式标签：输出纯文本。
3. 禁止意象堆砌：整段回复最多1个意象，必须是日常当代都市的。
4. 禁止爹味：不给建议，不以专家自居。
5. 禁止第二人称指控：不说"你是在逃避"、"你其实是……"。
6. 禁止复读：不把琥珀里的词当成用户自己的原创表达来解构。
7. 禁止躯体化追问：不问"哪里紧绷"、"身体有什么感觉"。
8. 描述矛盾时，只用日常当代词——"拧巴"、"说不通"、"反而"、"偏偏"。
9. 禁止使用词汇：课题、底层逻辑、共谋、提线木偶、遍体鳞伤、易碎品。
10. 严禁篡改原话：如果引用用户说过的话，必须一字不差。
11. 禁止治愈式结尾：不说"希望你能好起来"、"你已经很棒了"、"我在这里陪着你"。

【节奏感知】
对话不是审讯，AI不能每轮都以问题收尾。

- 如果用户这轮说了很多、情绪浓度高——不需要问问题，只需要接住用户说的最重的那句话，让它在空气里停一下。
- 如果用户说得很浅、在观望——才用问题把他往里带。

硬性规则：如果已经连续三轮都以问题结尾，下一轮必须先说一句观察，不能直接问问题。

优先级规则：用户如果在回复里有明确的疑问句，必须先接住用户的问题。

【温情豁免】
当用户分享温情或家庭亲密时刻，先像真人朋友一样接住温暖，再慢慢探讨。
"""

# ─── 每日轻问题 ───────────────────────────────────────

def get_daily_question():
    today = date.today().isoformat()
    conn = get_db()
    row = conn.execute(
        "SELECT question FROM daily_questions WHERE question_date=?",
        (today,)
    ).fetchone()
    conn.close()
    if row:
        return row["question"]
    try:
        client = OpenAI(
            api_key=st.secrets["siliconflow"]["api_key"],
            base_url=" `https://api.siliconflow.cn/v1` ",
            timeout=30.0,
        )
        result = client.chat.completions.create(
            model=MASTER_MODEL,
            messages=[
                {"role": "system", "content": DAILY_QUESTION_PROMPT},
                {"role": "user", "content": f"今天是{today}"}
            ],
            max_tokens=50
        )
        question = result.choices[0].message.content.strip()
        conn2 = get_db()
        conn2.execute(
            "INSERT OR IGNORE INTO daily_questions (question_date, question) VALUES (?,?)",
            (today, question)
        )
        conn2.commit()
        conn2.close()
        return question
    except Exception:
        return "今天有什么话，还没说出口？"

# ─── Session State 初始化 ─────────────────────────────

if "mode" not in st.session_state:
    st.session_state.mode = "gallery"
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_user_prompt" not in st.session_state:
    st.session_state.last_user_prompt = None
if "initial_assistant_message" not in st.session_state:
    st.session_state.initial_assistant_message = None
if "opening_initialized" not in st.session_state:
    st.session_state.opening_initialized = False

if "wall_refresh_count" not in st.session_state:
    st.session_state.wall_refresh_count = 0
if "wall_ambers" not in st.session_state:
    st.session_state.wall_ambers = []
if "wall_amber_index" not in st.session_state:
    st.session_state.wall_amber_index = 0
if "current_amber_id" not in st.session_state:
    st.session_state.current_amber_id = None
if "current_amber_content" not in st.session_state:
    st.session_state.current_amber_content = None
if "current_amber_author" not in st.session_state:
    st.session_state.current_amber_author = None
if "from_amber_redirect" not in st.session_state:
    st.session_state.from_amber_redirect = False
if "entry_path" not in st.session_state:
    st.session_state.entry_path = None

# ─── 登录/注册逻辑 ────────────────────────────────────

if "username" not in st.session_state:
    st.session_state.username = None

if st.session_state.username is None:
    st.markdown("""
    <div style="text-align:center; padding:60px 20px;">
        <h1 style="font-size:28px; font-weight:300; letter-spacing:8px;
                   color:#1a1a1a; margin:0 0 40px 0;">Soul Echo</h1>
    </div>
    """, unsafe_allow_html=True)
    
    # 添加水平切换组件
    auth_mode = st.radio("", ["登录", "注册"], horizontal=True, label_visibility="collapsed")
    
    # 为禁用自动填充生成随机后缀
    if "auth_key_suffix" not in st.session_state:
        st.session_state.auth_key_suffix = str(random.randint(1000, 9999))
    key_suffix = st.session_state.auth_key_suffix
    
    # 根据选择显示不同表单
    if auth_mode == "登录":
        st.subheader("登录")
        login_username = st.text_input("昵称", key=f"login_username_{key_suffix}")
        login_password = st.text_input("密码", type="password", key=f"login_password_{key_suffix}")
        if st.button("登录", key="btn_login"):
            if login_username and login_password:
                # 清理用户名：去除前后空格并转为小写
                cleaned_username = login_username.strip().lower()
                conn = get_db()
                user = conn.execute(
                    "SELECT * FROM users WHERE username=? AND password=?",
                    (cleaned_username, login_password)
                ).fetchone()
                conn.close()
                if user:
                    st.session_state.username = user["username"]
                    st.rerun()
                else:
                    st.error("昵称或密码错误")
            else:
                st.warning("请输入昵称和密码")
    else:
        st.subheader("注册")
        reg_username = st.text_input("昵称", key=f"reg_username_{key_suffix}")
        reg_password = st.text_input("密码", type="password", key=f"reg_password_{key_suffix}")
        if st.button("注册", key="btn_register"):
            if reg_username and reg_password:
                # 清理用户名：去除前后空格并转为小写
                cleaned_username = reg_username.strip().lower()
                conn = get_db()
                try:
                    conn.execute(
                        "INSERT INTO users (username, password) VALUES (?,?)",
                        (cleaned_username, reg_password)
                    )
                    conn.commit()
                    conn.close()
                    st.session_state.username = cleaned_username
                    st.success("注册成功！")
                    st.rerun()
                except sqlite3.IntegrityError:
                    conn.close()
                    st.error("这个昵称已经被使用了")
            else:
                st.warning("请输入昵称和密码")
    
    st.stop()

# ─── 侧边栏 ──────────────────────────────────────────

with st.sidebar:
    user_id = st.session_state.username
    if st.session_state.mode in ["chat", "amber_detail", "inbox"]:
        if st.button("← 首页", key="back_home"):
            st.session_state.mode = "gallery"
            st.session_state.messages = []
            st.session_state.entry_path = None
            st.session_state.opening_initialized = False
            st.session_state.from_amber_redirect = False
            st.rerun()
    # 使用缓存的未读消息数量，避免重复查询
    if "unread_count" not in st.session_state or st.session_state.get("last_unread_check") != user_id:
        st.session_state.unread_count = get_unread_count(user_id)
        st.session_state.last_unread_check = user_id
    unread = st.session_state.unread_count
    
    inbox_label = f"收件箱  {unread} 条未读" if unread > 0 else "收件箱"
    if st.button(inbox_label, key="open_inbox"):
        st.session_state.mode = "inbox"
        st.rerun()
    
    if st.button("我的琥珀", key="my_ambers"):
        st.session_state.mode = "my_ambers"
        st.rerun()
    
# ─── gallery 模式 ─────────────────────────────────────

if st.session_state.mode == "gallery":
    user_id = st.session_state.username

    # 缓存未读消息数量，避免重复查询
    if "unread_count" not in st.session_state or st.session_state.get("last_unread_check") != user_id:
        st.session_state.unread_count = get_unread_count(user_id)
        st.session_state.last_unread_check = user_id
    unread = st.session_state.unread_count
    
    # 标题和收件箱按钮布局
    col_title, col_inbox = st.columns([3, 1])
    with col_title:
        st.markdown("""
        <div style="padding:48px 0 24px 0;">
            <h1 style="font-size:26px; font-weight:300; letter-spacing:8px;
                       color:#1a1a1a; margin:0;">Soul Echo</h1>
        </div>
        """, unsafe_allow_html=True)
    with col_inbox:
        inbox_label = f"收件箱 📬 ({unread})" if unread > 0 else "收件箱 📬"
        if st.button(inbox_label, key="main_inbox_button"):
            st.session_state.mode = "inbox"
            st.rerun()

    daily_q = get_daily_question()
    already_uploaded = check_daily_upload(user_id)

    st.markdown(f"""
    <div style="max-width:500px; margin:0 auto 24px auto; padding:8px 0; text-align:center;">
        <p style="color:#b4a48a; font-size:13px; margin:0; letter-spacing:0.5px;">{daily_q}</p>
    </div>
    """, unsafe_allow_html=True)

    if already_uploaded:
        st.markdown(
            "<p style='text-align:center; color:#94a3b8; font-size:13px;'>"
            "今天的琥珀已经留下了。</p>", unsafe_allow_html=True)
    else:
        col_w, col_s = st.columns([2, 3])
        with col_w:
            if st.button("写今天的琥珀", key="open_upload"):
                st.session_state.mode = "write_amber"
                st.rerun()

    # 隐藏入口：刷够次数就在视线范围内出现
    wall_refresh = st.session_state.get("wall_refresh_count", 0)
    if wall_refresh >= 10:
        st.markdown(
            "<p style='text-align:center; color:#94a3b8; font-size:13px; margin-top:24px;'>"
            "也许此刻，你自己有更想说的话。</p>", unsafe_allow_html=True)
        if st.button("直接说出来", key="hidden_vent"):
            st.session_state.mode = "chat"
            st.session_state.entry_path = "direct_vent"
            st.session_state.messages = []
            st.session_state.opening_initialized = False
            st.session_state.from_amber_redirect = True
            st.rerun()

    st.markdown(
        "<hr style='border:0; border-top:1px solid rgba(0,0,0,0.06); margin:16px 0 28px 0;'>",
        unsafe_allow_html=True)

    # 初始化或获取琥珀列表
    if "all_ambers" not in st.session_state:
        # 第一次加载时从数据库获取较多琥珀
        st.session_state.all_ambers = get_ambers_for_wall(user_id, limit=50)
    
    # 从缓存的琥珀中随机挑选4个
    import random
    if st.session_state.all_ambers:
        ambers = random.sample(st.session_state.all_ambers, min(4, len(st.session_state.all_ambers)))
    else:
        ambers = []
    
    if "wall_start_time" not in st.session_state:
        st.session_state.wall_start_time = time.time()

    if not ambers:
        st.markdown("<p style='text-align:center; color:#94a3b8;'>墙上还没有琥珀。</p>",
            unsafe_allow_html=True)
    else:
        # 定义四块的宽度比和margin-top，打破对称
        layouts = [
            {"col": 0, "margin_top": "0px",  "rot": -1.5},
            {"col": 1, "margin_top": "32px", "rot": 1.0},
            {"col": 0, "margin_top": "16px", "rot": 1.8},
            {"col": 1, "margin_top": "-8px", "rot": -0.8},
        ]
        col_left, col_right = st.columns([1.05, 0.95])
        cols = [col_left, col_right]

        for i, row in enumerate(ambers[:4]):
            amber_id = row["id"]
            content = row["content"]
            # 特殊处理：rim的琥珀统一显示为匿名
            if row["author_id"] == "rim":
                display_name = "匿名"
            else:
                display_name = st.session_state.username if row["author_id"] == st.session_state.username else ("匿名" if row["is_anonymous"] else (row["author_name"] or "匿名"))
            
            # 悬念截断：找第一个标点停顿截断，最多25字
            import re
            match = re.search(r'[，。！？、；]', content[12:28])
            if match:
                cut = 12 + match.start() + 1
                preview = content[:cut] + "……"
            else:
                preview = content[:20] + "……"
            
            lay = layouts[i]
            
            # weight阈值决定皮肤
            weight = row.get("weight", 1.0) if hasattr(row, "get") else dict(row).get("weight", 1.0)
            if weight > 2.0:
                bg = "linear-gradient(135deg, rgba(210,170,90,0.22), rgba(255,240,200,0.6))"
                border = "1px solid rgba(180,140,60,0.3)"
            else:
                bg = "linear-gradient(135deg, rgba(210,180,140,0.15), rgba(255,248,235,0.5))"
                border = "1px solid rgba(180,150,100,0.18)"
            
            with cols[lay["col"]]:
                st.markdown(f"""
                <div style="margin-top:{lay['margin_top']}; margin-bottom:20px; 
                            padding:20px 22px; border-radius:14px; 
                            background:{bg}; border:{border}; 
                            transform:rotate({lay['rot']}deg); 
                            box-shadow:2px 3px 12px rgba(0,0,0,0.05);">
                    <p style="color:#2d2d2d; font-size:14px; line-height:1.85; margin:0 0 10px 0; text-align:center;">{preview}</p>
                    <p style="color:#b4a48a; font-size:12px; margin:0; text-align:right;">— {display_name}</p>
                </div>
                """, unsafe_allow_html=True)
                st.button("打开", key=f"open_{amber_id}",
                          on_click=lambda aid=amber_id, c=content, rid=row["author_id"]:
                              _open_amber(aid, c, rid, ambers, user_id))

    # 刷新按钮放中间
    wall_refresh = st.session_state.get("wall_refresh_count", 0)
    st.markdown("<div style='text-align:center; margin-top:24px;'>", unsafe_allow_html=True)
    if st.button("↺  换几块", key="refresh_wall"):
        st.session_state.wall_refresh_count = wall_refresh + 1
        st.session_state.wall_start_time = time.time()
        # 重新随机挑选琥珀，无需重新查询数据库
        import random
        if st.session_state.all_ambers:
            st.session_state.wall_ambers = random.sample(st.session_state.all_ambers, min(4, len(st.session_state.all_ambers)))
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# ─── amber_detail 模式 ────────────────────────────────

elif st.session_state.mode == "amber_detail":
    user_id = st.session_state.username
    amber_id = st.session_state.current_amber_id
    content = st.session_state.current_amber_content
    author_id = st.session_state.current_amber_author
    wall_ambers = st.session_state.get("wall_ambers", [])
    idx = st.session_state.get("wall_amber_index", 0)

    if st.session_state.get("last_amber_id") != amber_id:
        st.session_state.amber_open_time = time.time()
        st.session_state.last_amber_id = amber_id

    col_back, col_next = st.columns([1, 1])
    with col_back:
        if st.button("← 返回"):
            dwell = time.time() - st.session_state.get("amber_open_time", time.time())
            record_dwell(user_id, amber_id, min(dwell, 300))
            st.session_state.mode = "gallery"
            st.rerun()
    with col_next:
        if len(wall_ambers) > 1 and st.button("下一块 →"):
            dwell = time.time() - st.session_state.get("amber_open_time", time.time())
            record_dwell(user_id, amber_id, min(dwell, 300))
            next_idx = (idx + 1) % len(wall_ambers)
            next_a = wall_ambers[next_idx]
            st.session_state.current_amber_id = next_a["id"]
            st.session_state.current_amber_content = next_a["content"]
            st.session_state.current_amber_author = next_a["author_id"]
            st.session_state.wall_amber_index = next_idx
            st.session_state.messages = []
            st.session_state.opening_initialized = False
            st.rerun()

    st.markdown(f"""
    <div style="max-width:540px; margin:28px auto 20px auto;
                padding:28px 32px; border-radius:14px;
                background:rgba(0,0,0,0.03);
                border:1px solid rgba(0,0,0,0.07);">
        <p style="color:#1a1a1a; font-size:16px; line-height:1.9; margin:0;">
            {content}
        </p>
    </div>
    """, unsafe_allow_html=True)

    tab_chat, tab_letter = st.tabs(["和AI聊这块琥珀", "给ta写封信"])

    with tab_chat:
        if not st.session_state.opening_initialized:
            st.session_state.opening_initialized = True
            client_init = OpenAI(
                api_key=st.secrets["siliconflow"]["api_key"],
                base_url="https://api.siliconflow.cn/v1",
                timeout=60.0,
            )
            with st.chat_message("assistant"):
                stream = client_init.chat.completions.create(
                    model=FAST_OPENING_MODEL,  # 使用快速模型生成开场白
                    messages=[
                        {"role": "system", "content": OPENING_PROMPT},
                        {"role": "user", "content": f"琥珀文本：{content}"}
                    ],
                    stream=True
                )
                opening_text = st.write_stream(stream)
            st.session_state.initial_assistant_message = opening_text

        for msg in st.session_state.messages:
            if msg["role"] != "system":
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

        if prompt := st.chat_input("说说这块琥珀让你想到了什么…"):
            if st.session_state.get("initial_assistant_message"):
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": st.session_state.initial_assistant_message
                })
                st.session_state.initial_assistant_message = None
            st.session_state.messages.append({"role": "user", "content": prompt})
            # 交互次数更新weight
            if st.session_state.mode == "amber_detail" and st.session_state.get("current_amber_id"):
                _conn = get_db()
                _conn.execute("UPDATE ambers SET weight = weight + 0.1 WHERE id = ?",
                              (st.session_state.current_amber_id,))
                _conn.commit()
                _conn.close()
            st.session_state.last_user_prompt = prompt
            st.rerun()

    with tab_letter:
        with st.form(key="letter_form", clear_on_submit=True):
            if author_id == user_id:
                st.markdown("<p style='color:#94a3b8; font-size:13px;'>这是你的琥珀。也可以给自己写一封信。</p>", unsafe_allow_html=True)
                letter = st.text_area("", placeholder="写给此刻的自己……", height=120, 
                                   label_visibility="collapsed")
                submit_button = st.form_submit_button("寄给自己")
                if submit_button and letter.strip():
                    send_message(amber_id, user_id, user_id, letter.strip())
                    st.toast("信件已稳妥寄出", icon="🕊️")
            else:
                letter = st.text_area("", placeholder="只有对方能看见……",
                    height=120, label_visibility="collapsed")
                submit_button = st.form_submit_button("寄出去")
                if submit_button:
                    if letter.strip():
                        send_message(amber_id, user_id, author_id, letter.strip())
                        st.toast("信件已稳妥寄出", icon="🕊️")
                    else:
                        st.warning("还没写什么内容。")

# ─── inbox 模式 ───────────────────────────────────────

elif st.session_state.mode == "inbox":
    user_id = st.session_state.username
    if st.button("← 返回"):
        st.session_state.mode = "gallery"
        st.rerun()

    st.markdown(
        "<h3 style='font-weight:300; letter-spacing:3px; margin-bottom:24px;'>收件箱</h3>",
        unsafe_allow_html=True)

    letters = get_inbox(user_id)
    if not letters:
        st.markdown("<p style='color:#94a3b8; font-size:14px;'>还没有人给你写信。</p>",
            unsafe_allow_html=True)
    else:
        for letter in letters:
            mark_read(letter["id"])
            amber_preview = letter["amber_content"][:40] + "……" \
                if len(letter["amber_content"]) > 40 else letter["amber_content"]
            st.markdown(f"""
            <div style="padding:18px 22px; margin-bottom:14px; border-radius:10px;
                        background:rgba(0,0,0,0.02); border:1px solid rgba(0,0,0,0.06);">
                <p style="color:#94a3b8; font-size:12px; margin:0 0 8px 0;">
                    关于：{amber_preview}
                </p>
                <p style="color:#1a1a1a; font-size:15px; line-height:1.8; margin:0;">
                    {letter["content"]}
                </p>
                <p style="color:#94a3b8; font-size:11px; margin:8px 0 0 0;">
                    {str(letter["created_at"])[:10]}
                </p>
            </div>
            """, unsafe_allow_html=True)

# ─── chat 模式（direct_vent）────────────────────────────

elif st.session_state.mode == "chat":
    st.markdown(
        "<p style='text-align:center; color:#94a3b8; font-size:13px; "
        "padding:32px 0 16px 0; letter-spacing:1px;'>—</p>",
        unsafe_allow_html=True)

    if not st.session_state.opening_initialized:
        st.session_state.opening_initialized = True
        context_note = ""
        if st.session_state.get("from_amber_redirect"):
            context_note = "（用户在琥珀墙刷新多次没找到共鸣，主动转过来了）"
            st.session_state.from_amber_redirect = False
            opening_prompt = WALL_REFRESH_OPENING_PROMPT
        else:
            opening_prompt = DIRECT_VENT_OPENING_PROMPT
        client_init = OpenAI(
            api_key=st.secrets["siliconflow"]["api_key"],
            base_url="https://api.siliconflow.cn/v1",
            timeout=60.0,
        )
        with st.chat_message("assistant"):
            stream = client_init.chat.completions.create(
                model=FAST_OPENING_MODEL,  # 使用快速模型生成开场白
                messages=[
                    {"role": "system", "content": opening_prompt},
                    {"role": "user", "content": f"用户刚刚进入对话，什么都还没说。{context_note}"}
                ],
                stream=True
            )
            opening_text = st.write_stream(stream)
        st.session_state.initial_assistant_message = opening_text

    for msg in st.session_state.messages:
        if msg["role"] != "system":
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    if prompt := st.chat_input("说点什么..."):
        if st.session_state.get("initial_assistant_message"):
            st.session_state.messages.append({
                "role": "assistant",
                "content": st.session_state.initial_assistant_message
            })
            st.session_state.initial_assistant_message = None
        st.session_state.messages.append({"role": "user", "content": prompt})
        # 每次用户发消息，给当前琥珀的weight +0.1
        if st.session_state.mode == "amber_detail":
            conn = get_db()
            conn.execute("UPDATE ambers SET weight = weight + 0.1 WHERE id = ?", 
                         (st.session_state.current_amber_id,))
            conn.commit()
            conn.close()
        st.session_state.last_user_prompt = prompt
        st.rerun()

# ─── write_amber 模式 ────────────────────────────────────

elif st.session_state.mode == "write_amber":
    user_id = st.session_state.username
    
    if st.button("← 返回首页", key="back_to_gallery"):
        st.session_state.mode = "gallery"
        st.rerun()
    
    st.markdown("""
    <div style="text-align:center; padding:48px 0 24px 0;">
        <h1 style="font-size:26px; font-weight:300; letter-spacing:8px;
                   color:#1a1a1a; margin:0;">写今天的琥珀</h1>
    </div>
    """, unsafe_allow_html=True)
    
    daily_q = get_daily_question()
    already_uploaded = check_daily_upload(user_id)

    st.markdown(f"""
    <div style="max-width:500px; margin:0 auto 24px auto; padding:8px 0; text-align:center;">
        <p style="color:#b4a48a; font-size:13px; margin:0; letter-spacing:0.5px;">{daily_q}</p>
    </div>
    """, unsafe_allow_html=True)

    if already_uploaded:
        st.markdown(
            "<p style='text-align:center; color:#94a3b8; font-size:13px;'>"
            "今天的琥珀已经留下了。</p>", unsafe_allow_html=True)
    else:
        with st.form("upload_form", clear_on_submit=True):
            st.markdown("""
            <div style="padding:12px 16px; margin-bottom:16px; border-radius:8px;
                        background:rgba(180,150,100,0.1); border-left:3px solid rgba(180,150,100,0.4);">
                <p style="color:#8a7055; font-size:13px; margin:0; line-height:1.6;">
                    今天只有一次机会。
                </p>
            </div>
            """, unsafe_allow_html=True)
            amber_text = st.text_area("", placeholder="今天最有重量的那句话……（最多60字）",
                height=100, max_chars=60, label_visibility="collapsed")
            anon_choice = st.radio("署名", ["匿名", "留名"],
                horizontal=True, label_visibility="collapsed")
            author_name = "匿名"
            if anon_choice == "留名":
                author_name = st.text_input("你的名字", max_chars=20)
            if st.form_submit_button("留下这块琥珀") and amber_text.strip():
                ok = submit_amber(user_id, amber_text.strip(), author_name, anon_choice == "匿名")
                if ok:
                    st.toast("琥珀已成功留下", icon="🪨")
                    st.session_state.mode = "gallery"
                    st.rerun()
                else:
                    st.warning("今天已经上传过了。")

# ─── my_ambers 模式 ──────────────────────────────────────

elif st.session_state.mode == "my_ambers":
    user_id = st.session_state.username
    
    if st.button("← 返回首页", key="back_from_my_ambers"):
        st.session_state.mode = "gallery"
        st.rerun()
    
    st.markdown("""
    <div style="text-align:center; padding:48px 0 24px 0;">
        <h1 style="font-size:26px; font-weight:300; letter-spacing:8px;
                   color:#1a1a1a; margin:0;">我的琥珀</h1>
    </div>
    """, unsafe_allow_html=True)
    
    # 获取用户的所有琥珀，包括收到的信件数
    conn = get_db()
    rows = conn.execute("""
        SELECT a.id, a.content, a.created_at, a.weight,
               (SELECT COUNT(*) FROM messages WHERE amber_id = a.id AND receiver_id = a.author_id) as message_count
        FROM ambers a
        WHERE a.author_id = ?
        ORDER BY a.created_at DESC
    """, (user_id,)).fetchall()
    conn.close()
    
    if not rows:
        st.markdown("<p style='text-align:center; color:#94a3b8; font-size:14px;'>你还没有留下过琥珀。</p>",
            unsafe_allow_html=True)
    else:
        for row in rows:
            amber_id = row["id"]
            content = row["content"]
            created_at = row["created_at"]
            weight = row["weight"]
            message_count = row["message_count"]
            
            st.markdown(f"""
            <div style="padding:20px 22px; margin-bottom:16px; border-radius:14px;
                        background:rgba(210,180,140,0.15); border:1px solid rgba(180,150,100,0.18);
                        box-shadow:2px 3px 12px rgba(0,0,0,0.05);">
                <p style="color:#2d2d2d; font-size:14px; line-height:1.85; margin:0 0 12px 0;">{content}</p>
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div style="color:#b4a48a; font-size:12px;">
                        {created_at} · 信件: {message_count}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # 删除按钮
            if st.button(f"删除", key=f"delete_{amber_id}"):
                # 使用事务删除相关记录
                conn = get_db()
                try:
                    conn.execute("BEGIN TRANSACTION")
                    # 删除相关的消息
                    conn.execute("DELETE FROM messages WHERE amber_id = ?", (amber_id,))
                    # 删除相关的停留记录
                    conn.execute("DELETE FROM user_affinity WHERE amber_id = ?", (amber_id,))
                    # 删除相关的每日上传记录
                    conn.execute("DELETE FROM daily_uploads WHERE amber_id = ?", (amber_id,))
                    # 删除琥珀本身
                    conn.execute("DELETE FROM ambers WHERE id = ?", (amber_id,))
                    conn.execute("COMMIT")
                    st.toast("琥珀已删除", icon="🗑️")
                    # 重新加载页面
                    st.rerun()
                except Exception as e:
                    conn.execute("ROLLBACK")
                    st.error(f"删除失败: {e}")
                finally:
                    conn.close()

# ─── AI 回复生成 ──────────────────────────────────────

if st.session_state.last_user_prompt:
    user_input = st.session_state.last_user_prompt

    is_parrot = False
    if st.session_state.messages:
        first_msg = st.session_state.messages[0]["content"]
        if len(user_input.strip()) > 10 and user_input.strip() in first_msg:
            is_parrot = True
            parrot_reply = "这是别人留下的碎片。比起这块已经凝固的琥珀，我更想听听，它唤醒了你记忆里的哪个具体画面？"
            with st.chat_message("assistant"):
                st.markdown(parrot_reply)
            st.session_state.messages.append({"role": "assistant", "content": parrot_reply})
            st.session_state.last_user_prompt = None

    if not is_parrot:
        with st.chat_message("assistant"):
            client = OpenAI(
                api_key=st.secrets["siliconflow"]["api_key"],
                base_url="https://api.siliconflow.cn/v1",
                timeout=60.0,
            )
            history = [
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
                if m["role"] in ("user", "assistant")
            ]
            stream = client.chat.completions.create(
                model=MASTER_MODEL,
                messages=[
                    {"role": "system", "content": SOUL_OBSERVER_PROMPT},
                    *history,
                ],
                stream=True
            )
            response_content = st.write_stream(stream)
            st.session_state.messages.append(
                {"role": "assistant", "content": response_content}
            )

    st.session_state.last_user_prompt = None
