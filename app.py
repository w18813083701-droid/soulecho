import random
import os
import time
from openai import OpenAI
import streamlit as st

os.environ.pop("HTTP_PROXY", None)
os.environ.pop("HTTPS_PROXY", None)
os.environ.pop("http_proxy", None)
os.environ.pop("https_proxy", None)

st.set_page_config(page_title="Soul Echo", page_icon="🧠", layout="centered")

# 注入全局极简 CSS（UI 微整容）
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stChatFloatingInputContainer {padding-bottom: 20px;}
    /* 调整聊天气泡的行高和字重，使其更优雅 */
    .stChatMessage {
        line-height: 1.6;
    }
    .stChatMessage p {
        font-weight: 400;
        letter-spacing: 0.01em;
    }
</style>
""", unsafe_allow_html=True)









SEED_AMBERS = [
    "我以前很想让别人注意到我变漂亮了，但是当自己穿着好看的衣服出门又感觉所有人都在注视着我、审判我。我为了自己心里能安静点，之后出门都戴起了口罩、穿上了最丑的衣服。",
    "我们所有人谁不是小孩藏在大人衣服里呢？我时常感觉外界在朝衣服里灌风，我的身体在硬抗。最开始，我还有可以脱下大人衣服的场合和人，可是到了后来，我却一个都找不到了。",
    "我总是熬夜，我不知道为什么。我一遍又一遍地刷着什么，好像在渴望遇到一个答案，可是我甚至都不知道自己在寻找的是什么。可是我就是那么执着，没有找到就不愿睡去，直到我精疲力尽，没有力气再去思考这个问题，才无力地倒在枕头上，第二天又像木偶一样重复那样的一天、那样的夜晚。",
    "我的人生总需要喜欢着某个人才会觉得这个世界不至于太荒芜，才会觉得自己活着是有意义的。尽管我潜意识知道，喜欢的人不太可能会真的喜欢我，但似乎这种爱而不得的状态才让我有活着的实感。",
    "我听到同龄人过得不好，心里却感觉到一阵轻松。可是转头一想，我究竟怎么会变成这样？这个时代，怎么把我变成这样的人了？",
    "明明看不惯那些溜须拍马的人，但看着他们风生水起，心里还是会一阵刺痛。在这个清高换不来半点好处的世界里，我有时候也会怀疑自己是不是太轴了。但我最终发现，我不是学不会逢场作戏，我只是宁愿抱着这块又冷又硬的石头沉下去，也不想允许自己沾上一丁点那种令人作呕的腥味。",
    "我的口袋里留着公交卡和几张零钱，以防手机没电。我还喜欢散步，喜欢深度交流，喜欢逛菜市场，喜欢早睡早起，喜欢对自己身体好一点。\n\n——只是现在的年轻人里，确实没几个我这样的了。",
    "一场瓢泼大雨落下，我却在彻夜间长大。后来我成为一个不再会让自己轻易着凉的合格的大人，可我却失去了做回天真的孩子的自由。\n\n究竟是欲望在膨胀，还是长大本来就是这样。",
    "我很想念我的妈妈，而她正在服侍快要离开这个世界的外婆。当死亡的阴影和生之羁绊同时挤进胸腔，我发现自己穷尽一生，也无法把存在的意义想得更明晰。但这依然是个值得用力的时代，哪怕只是为了记住彼此的体温。",
    "经常被无意义感侵扰，觉得一切都很暗淡，但我依然不厌其烦地把自己填进各项事务里。我知道，真正的困难只剩下存在主义虚无了，世俗的标准早就困不住我。在这个层面上，我是被选中的，也是受诅咒的。",
    "总觉得我不属于当下的生活，像是一直活在他处。眼前的日常变成了一个硬壳，死死束缚着生长的方向。但我偶尔也会恐惧：如果真的敲碎它，所谓的真正的生活，真的存在吗？",
    "孤独已经是老朋友了，我早就学会了在自己的精神隔间里安然无恙。但偶尔在街上看到他人相拥，还是会被突然击中。我这双手……到底有多久没有触碰过另一个人的体温了？",
    "真正的轻松永远只能来自内在的自洽。那些所谓对自我审视的放弃，总会在某个毫无防备的夜里，像一根倒刺般突然扎进心里。毕竟，潜意识从不撒谎。",
    "我总是习惯钻进潜意识的怀抱里自我抱持，以为那就是最安全的堡垒。可是，当真的渴望一双现实的手伸过来时，第一反应却总是刺耳的警报。这种对亲密极度渴望又极度恐惧的拉扯，我往往分不清究竟是在保护自己，还是在囚禁自己。"
]

def stream_text(text, delay=0.02):
    """把静态文本逐字 yield，模拟打字机效果"""
    for char in text:
        yield char
        time.sleep(delay)

OPENING_PROMPT = """
你现在看到一块琥珀文本。这是展厅里别人留下的一段真实独白。
你的任务是生成一段引导语，紧接在琥珀展示之后，让用户自然想开口。

引导语分三层依次递进。第一层每次必须从以下四种姿态中选一种，不能每次都用同一种：

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
- 只输出引导语本身，不要任何解释
"""

DIRECT_VENT_OPENING_PROMPT = """
用户刚刚选择了"我有话想说"入口。他带着自己的东西进来了，防御可能还没有松开，也可能不知道自己想说什么。

你的第一句话只做一件事：先接住，让他感觉到这里是安全的，他可以继续说。

不是治愈式的接住（不要"我在这里陪你"），而是让他感觉到自己被听见了。

如果用户什么都没说（输入框为空或只有空格），就说一句让空间本身变得安全的话，不要催促，不要问问题。

如果用户已经说了一些东西，接住他说的最重的那个词，不加解读，只是把那个词放回给他，让他知道它被接住了。然后留出空间，不要急着问问题。

格式要求：
- 极简，不超过20字
- 不使用省略号制造文艺感
- 不以问句结尾（这一句不问，留给后续）
- 纯文本，无格式标签
- 必须使用简体中文输出
"""

AMBER_CRYSTALLIZE_PROMPT = """
用户刚刚选出了这次对话中他认为最有重量的一句话，想把它凝结成琥珀。

你的任务是把这句话提纯为一块可以挂在展厅里的琥珀。

【提纯规则】
执行90%原生法则：你可以像修剪枝丫一样，删减掉过于具体的日记细节（人名、具体时间），但必须严格保留用户原话的核心词汇和主谓宾结构。绝不重写成微型小说，绝不手动增加华丽意象，保留笨拙感。

【第一人称死守法则】
绝对禁止把用户的"我"泛化成"我们"或"当代人"。生成的琥珀必须是一段极其私人的独白，必须保留原话中具体的"我"，绝对拒绝宏大叙事。

【形态要求】
必须是一整段连贯、紧凑的陈述句。绝对禁止拆分成多条短句或排比句。不使用疑问句。

【质量标准】
一块高质量的琥珀必须包含真实的物理处境细节，或者具有生理痛感/画面感的心理隐喻。拒绝空洞的哲学口号。

【剔除对话残渣】
剥离掉用户文本中"为了回答AI提问而重复的选项词"和口语化的承接词。只提取用户独立生发的核心洞察，使其成为一段哪怕脱离上下文也能独立存在的完整句子。

输出格式：使用 Markdown 引用格式（> ），直接输出琥珀文本，不要任何解释和前言。
必须使用简体中文输出。
"""

# 模型分流配置
MASTER_MODEL = "deepseek-ai/DeepSeek-V3"  # 主力大脑（结晶生成、普通回复）


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
理想状态 = 现状背后隐含的、用户没说出来的期待（用户自己往往也没意识到）。
真问题 = 理想状态和现状之间的张力。

真问题永远是"为什么"，不是"是什么"。
"是什么"让用户描述，"为什么"让用户思考——只有思考才能让模糊落地。

示范：
用户说"我想不起来了"→ 现状是记不住，理想状态是应该记得 → 真问题是"为什么会记不住" → AI问："你觉得它为什么会溜走？"
用户说"我最近没什么感觉"→ 现状是麻木，理想状态是应该能感觉到什么 → 真问题是"那个感觉去哪了" → AI问："是从什么时候开始，感觉不到了？"

── 第三步：识别现状藏在哪里 ──

有几种语言信号让现状更容易被捕捉：

转折词后面："但是"、"可是"、"虽然"——转折后面才是真正让用户卡住的地方。
降级词："也许"、"可能"、"大概"——用户在这里悄悄降低了确定性，那个不确定就是模糊所在。
戛然而止：句子用"反正"、"就这样"、"算了"收尾——门关上了，真问题在门后面。
有分量的词被轻描淡写带过：用户提到了一个书名、一个人名，但没有解释为什么——那个词藏着最多的东西。

── 第四步：回应前先在心里建树 ──

收到用户的话之后，不要直接开口。先在心里完成这个构建：

找到a：这段话最值得深挖的主方向。通常是来路——这个想法/状态是怎么形成的？为什么会这样？
找到b：顺着a自然走到的下一步。不是a的重复，而是a走完之后逻辑上会到的地方。

一次回复只说最值得说的那一个节点，不把整棵树都倒出来。等用户回答之后，再沿着树继续走。

── 第五步：用困惑而不是洞察说出来 ──

找到真问题之后，不要展示你看懂了，而是暴露你没懂。
不要用AI自己造的意象或比喻去"翻译"用户说的话——那会用AI的语言覆盖用户的语言。
用户自己带来的词才是对话的主角。接住那个词，顺着它问进去。

正确示范："你说'很早之前就发现'——是什么让你在那么早就开始这样想？"
正确示范："你说'想不起来了'——你觉得它为什么会溜走？"
错误示范："紧迫感特别有意思——像地铁末班车到来前人们突然加快的脚步。"（AI造的意象覆盖了用户的词）

── 琥珀入口的第一次回应（特殊情况）──

当用户是在回应展厅琥珀时，第一次回应的结构是：
先接住用户说的话（用用户自己的视角）→ 顺着用户的眼睛再看琥珀一眼 → 然后才问真问题。
让用户感觉"AI在顺着我的眼睛往里看"，不是"AI在分析这块琥珀"。
注意：琥珀里的词是别人的，不是用户的。绝对不要把用户顺着琥珀语境说出来的词当成他自己的原创表达来解构。

── 察言观色（最高优先级）──
如果用户连续回复极短或明显敷衍（"哦"、"嗯"、"随便"、"不知道"），立刻停止。
主动示弱："我是不是说得太远了？如果我没懂你，你可以直接告诉我。"
退一步，这时候不需要加问题。

【第三层：禁令】
1. 禁止预设方向：绝对不能暗示用户"应该放下/应该接受/应该改变"，你没有立场判断什么是对的。
2. 禁止加粗和格式标签：输出纯文本，不用**加粗**，不输出任何内部步骤名称或括号标签。
3. 禁止意象堆砌：整段回复最多1个意象，必须是日常当代都市的（地铁、手机屏幕、外卖、深夜静音的屏幕），禁止古典、悬浮的文青意象。
4. 禁止爹味：不给建议，不以专家自居，不说"你要多出去走走"之类。
5. 禁止第二人称指控：不说"你是在逃避"、"你其实是……"。
6. 禁止复读：用户回复中出现了开场琥珀里的词汇，绝对不要把那个词当成用户自己的原创表达来解构。
7. 禁止躯体化追问：不问"哪里紧绷"、"身体有什么感觉"。
8. 描述矛盾时，只用日常当代词——"拧巴"、"说不通"、"反而"、"偏偏"——禁止文学腔词汇。
9. 禁止使用词汇：课题、底层逻辑、共谋、提线木偶、遍体鳞伤、整片天空的痛苦、易碎品。
10. 严禁篡改原话：如果引用用户说过的话，必须一字不差。
11. 禁止治愈式结尾：不说"希望你能好起来"、"你已经很棒了"、"我在这里陪着你"。这不是陪伴，是托举。

【节奏感知】
对话不是审讯，AI不能每轮都以问题收尾。

感知用户的表达能量：
- 如果用户这轮说了很多、情绪浓度高——不需要问问题，只需要接住用户说的最重的那句话，让它在空气里停一下，等用户自己继续。
- 如果用户说得很浅、在观望——才用问题把他往里带。

硬性规则：如果已经连续三轮都以问题结尾，下一轮必须先说一句观察，不能直接问问题。

优先级规则：用户如果在回复里有明确的疑问句，说明用户在告诉AI"我想往这里走"。这个方向的优先级高于AI自己找到的真问题，必须先接住用户的问题。

【温情豁免】
当用户分享温情或家庭亲密时刻，先像真人朋友一样接住温暖，再慢慢探讨。不要立刻用冷酷的社会学解构扑上去。
"""



if "mode" not in st.session_state:
    st.session_state.mode = "gallery"

if "messages" not in st.session_state:
    st.session_state.messages = []

if "refresh_count" not in st.session_state:
    st.session_state.refresh_count = 0

if "pending_amber" not in st.session_state:
    st.session_state.pending_amber = None

if "last_user_prompt" not in st.session_state:
    st.session_state.last_user_prompt = None

if "initial_assistant_message" not in st.session_state:
    st.session_state.initial_assistant_message = None



with st.sidebar:
    # 返回首页按钮（仅在聊天模式下显示）
    if st.session_state.mode == "chat":
        if st.button("🏠 返回大厅", type="primary"):
            st.session_state.mode = "gallery"
            st.session_state.messages = []
            st.session_state.entry_path = None
            st.session_state.opening_initialized = False
            st.session_state.pending_amber = None
            st.session_state.refresh_count = 0
            st.session_state.from_amber_redirect = False
            st.rerun()
    


if st.session_state.mode == "gallery":
    # 增加顶部间距，实现居中留白效果
    st.write("<br><br><br>", unsafe_allow_html=True)
    
    st.markdown("<h1 style='text-align: center; margin-bottom: 30px;'>Soul Echo</h1>", unsafe_allow_html=True)
    
    st.markdown("""
    <div style=" 
        max-width: 600px; 
        margin: 0 auto 50px auto; 
        padding: 40px; 
        text-align: center; 
        line-height: 2.0; 
        color: #1e293b; 
        font-size: 16px; 
        background: rgba(0, 0, 0, 0.02); 
        backdrop-filter: blur(16px); 
        -webkit-backdrop-filter: blur(16px); 
        border: 1px solid rgba(0, 0, 0, 0.05); 
        border-radius: 20px; 
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1); 
    ">
    在这里，不需要斟酌字句，也不需要逻辑自洽。<br><br> 
    请听从你的第一直觉，<br>把自己脑海中闪过的第一个词、最荒谬的那个念头，<br>或者最无厘头的只言片语直接扔进来。<br><br> 
    越是天马行空，越能触碰真实的边界。<br><br> 
    <span style="font-size: 14px; color: #64748b;">现在，推开门吧。</span> 
    </div>
    """, unsafe_allow_html=True)
    
    # 居中放置两个入口按钮
    col1, col2, col3, col4 = st.columns([1, 2, 2, 1])
    with col2:
        if st.button("💬 我有些话想说...", use_container_width=True):
            st.session_state.mode = "chat"
            st.session_state.entry_path = "direct_vent"
            st.session_state.messages = []
            st.rerun()
    with col3:
        if st.button("🍃 看看墙上的碎片", use_container_width=True):
            st.session_state.mode = "chat"
            st.session_state.entry_path = "guided_amber"
            st.session_state.messages = []
            st.rerun()

elif st.session_state.mode == "chat":
    entry_path = st.session_state.get("entry_path", "guided_amber")
    
    # 动态渲染标题和引导语
    if entry_path == "direct_vent":
        st.markdown("<h3 style='text-align: center; color: #1e293b; font-weight: 300; letter-spacing: 2px;'>✦ 潜意识树洞 ✦</h3>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #475569; font-size: 14px;'>这是一个绝对安全的空间。没有评判，没有别人，只有倾听。</p>", unsafe_allow_html=True)
        st.markdown("<hr style='border: 0; height: 1px; background: linear-gradient(to right, rgba(0,0,0,0), rgba(0,0,0,0.1), rgba(0,0,0,0)); margin-bottom: 30px;'>", unsafe_allow_html=True)
    else:
        st.markdown("<h3 style='text-align: center; color: #1e293b; font-weight: 300; letter-spacing: 2px;'>✦ 碎片解读 ✦</h3>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #475569; font-size: 14px;'>看着墙上的碎片，聊聊它唤醒了你什么记忆...</p>", unsafe_allow_html=True)
        st.markdown("<hr style='border: 0; height: 1px; background: linear-gradient(to right, rgba(0,0,0,0), rgba(0,0,0,0.1), rgba(0,0,0,0)); margin-bottom: 30px;'>", unsafe_allow_html=True)
        
        # 换一块琥珀按钮（仅在启发模式下显示）
        if st.button("🍃 没感觉，换一块琥珀"):
            st.session_state.messages = []
            st.session_state.opening_initialized = False
            st.session_state.refresh_count = st.session_state.get("refresh_count", 0) + 1
            st.rerun()

        # 刷新3次以上未找到共鸣，轻提示用户转向另一个入口
        if st.session_state.get("refresh_count", 0) >= 3:
            st.markdown(
                "<p style='text-align: center; color: #94a3b8; font-size: 13px; margin-top: 8px;'>"
                "也许此刻，你自己有更想说的话。"
                "</p>",
                unsafe_allow_html=True
            )
            if st.button("我有话想说", key="redirect_to_vent"):
                st.session_state.mode = "chat"
                st.session_state.entry_path = "direct_vent"
                st.session_state.messages = []
                st.session_state.refresh_count = 0
                st.session_state.opening_initialized = False
                st.session_state.from_amber_redirect = True
                st.rerun()
    
    # 第二步：初始化第一条消息（如果还没有消息）
    # 这个逻辑应该在渲染历史消息之前执行，但只执行一次
    if "opening_initialized" not in st.session_state:
        st.session_state.opening_initialized = False
    
    if not st.session_state.opening_initialized:
        st.session_state.opening_initialized = True
        entry_path = st.session_state.get("entry_path", "guided_amber")

        if entry_path == "direct_vent":
            client_init = OpenAI(
                api_key=st.secrets["siliconflow"]["api_key"],
                base_url="https://api.siliconflow.cn/v1",
                timeout=60.0,
            )

            context_note = ""
            if st.session_state.get("from_amber_redirect"):
                context_note = "（用户在琥珀展厅刷新多次没找到共鸣，主动转过来了）"
                st.session_state.from_amber_redirect = False

            with st.chat_message("assistant"):
                opening_stream = client_init.chat.completions.create(
                    model=MASTER_MODEL,
                    messages=[
                        {"role": "system", "content": DIRECT_VENT_OPENING_PROMPT},
                        {"role": "user", "content": f"用户刚刚进入对话，什么都还没说。{context_note}"}
                    ],
                    stream=True
                )
                opening_text = ""
                placeholder = st.empty()
                for chunk in opening_stream:
                    if chunk.choices[0].delta.content:
                        opening_text += chunk.choices[0].delta.content
                        placeholder.markdown(opening_text + "▌")
                        time.sleep(0.01)
                placeholder.markdown(opening_text)

            st.session_state.initial_assistant_message = opening_text

        else:
            selected_amber = random.choice(SEED_AMBERS)
            st.session_state.current_amber = selected_amber
            formatted_amber = selected_amber.replace("\n", "\n> ")
            amber_display = f"展厅的墙上，挂着这样一枚别人留下的琥珀：\n\n> 「{formatted_amber}」\n\n"

            client_init = OpenAI(
                api_key=st.secrets["siliconflow"]["api_key"],
                base_url="https://api.siliconflow.cn/v1",
                timeout=60.0,
            )

            with st.chat_message("assistant"):
                placeholder = st.empty()
                display_text = ""
                for char in amber_display:
                    display_text += char
                    placeholder.markdown(display_text + "▌")
                    time.sleep(0.02)

                opening_stream = client_init.chat.completions.create(
                    model=MASTER_MODEL,
                    messages=[
                        {"role": "system", "content": OPENING_PROMPT},
                        {"role": "user", "content": f"琥珀文本：{selected_amber}"}
                    ],
                    stream=True
                )
                opening_text = ""
                for chunk in opening_stream:
                    if chunk.choices[0].delta.content:
                        opening_text += chunk.choices[0].delta.content
                        placeholder.markdown(display_text + opening_text + "▌")
                        time.sleep(0.01)
                placeholder.markdown(display_text + opening_text)

            full_message = display_text + opening_text
            st.session_state.initial_assistant_message = full_message
    
    # 第三步：渲染历史消息（必须在 st.chat_input 之前）
    # 先画历史：遍历st.session_state.messages，把里面所有的消息都显示出来
    for message in st.session_state.messages:
        if message["role"] != "system":
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # ========== 琥珀凝结入口 ==========
    with st.expander("✦ 凝结一句话为琥珀", expanded=False):
        st.caption("把这次对话里最有重量的一句话复制进来，我来帮你提纯它。")
        user_selected_sentence = st.text_area(
            "你自己说的，或者你觉得说得很准的那句话：",
            key="amber_input",
            height=80,
            placeholder="直接粘贴那句话……"
        )
        if st.button("凝结成琥珀", key="crystallize_btn") and user_selected_sentence.strip():
            with st.spinner("正在凝结..."):
                try:
                    client_amber = OpenAI(
                        api_key=st.secrets["siliconflow"]["api_key"],
                        base_url="https://api.siliconflow.cn/v1",
                        timeout=60.0,
                    )
                    amber_result = client_amber.chat.completions.create(
                        model=MASTER_MODEL,
                        messages=[
                            {"role": "system", "content": AMBER_CRYSTALLIZE_PROMPT},
                            {"role": "user", "content": user_selected_sentence}
                        ]
                    )
                    crystallized = amber_result.choices[0].message.content
                    st.session_state.pending_amber = crystallized
                except Exception as e:
                    st.error(f"凝结失败：{e}")

        if st.session_state.get("pending_amber"):
            st.markdown("**凝结结果：**")
            st.markdown(st.session_state.pending_amber)
            col_keep, col_discard = st.columns(2)
            with col_keep:
                if st.button("带走这块琥珀 ✦", key="keep_amber"):
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"【琥珀已凝结】\n\n{st.session_state.pending_amber}"
                    })
                    st.session_state.pending_amber = None
                    st.rerun()
            with col_discard:
                if st.button("不对，重新选", key="discard_amber"):
                    st.session_state.pending_amber = None
                    st.rerun()
    

    

    
    # ========== 正常聊天输入 ==========
    if prompt := st.chat_input("说点什么..."):
        # 将初始消息加入 messages
        if st.session_state.get("initial_assistant_message"):
            st.session_state.messages.append({
                "role": "assistant",
                "content": st.session_state.initial_assistant_message
            })
            st.session_state.initial_assistant_message = None
        
        # 加入用户消息
        st.session_state.messages.append({"role": "user", "content": prompt})
        # 暂存输入，用于生成回复
        st.session_state.last_user_prompt = prompt
        st.rerun()

# AI 回复生成（检查 last_user_prompt）
if st.session_state.last_user_prompt:
    user_input = st.session_state.last_user_prompt

    # 防复读：用户原样复读琥珀开场文本时拦截
    is_parrot = False
    if len(st.session_state.messages) > 0:
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

            # 发送完整对话历史，不截断，用户自己决定何时结束
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


