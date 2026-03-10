import random
import os
import time
import threading
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

REFEREE_PROMPT = (
    "你现在的任务是测量用户文本的【共鸣温度】，输出一个 0 到 100 之间的加分值（格式如 [SCORE: 20]）。"
    "- [SCORE: 0]：字数极少、单薄的情绪宣泄（如'好烦'、'就是这样'）。无结构，无细节。"
    "- [SCORE: 15]：中等质量，顺着框架进行的理性分析或平淡叙述。"
    "- [SCORE: 40]：高质量，包含真实的物理处境细节或具有生理痛感/画面感的高密度心理隐喻（例如：'像倒刺扎进心里'），或者暴露了真实的痛感。"
    "- [SCORE: 80]：核弹级共鸣，极致的脆弱剖析，或极具张力的生活化温情瞬间。"
    "只输出 [SCORE: XX] 格式，不要输出任何其他内容。"
    "【最高格式防线】：你必须且只能以固定格式输出两个标签（例如：\n[SCORE: 30]\n[MATERIAL: OBSIDIAN]\n），【绝对禁止】附带任何解释废话！"
    "【材质与分数判定】："
    "1. 现实锚点（琥珀路径）：如果文本有具体的物理现实场景（人/事/物），正常打分，并输出 `[MATERIAL: AMBER]`。"
    "2. 纯粹精神（黑曜石路径）：如果文本是极度深邃的哲学思辨、潜意识剖析，缺乏具体物理锚点，【不要压低分数】，请根据深刻程度正常给高分（30-40分），并输出 `[MATERIAL: OBSIDIAN]`。"
    "必须使用简体中文输出。"
)

AMBER_GENERATOR_PROMPT = """
你现在是情绪美术馆的馆长，需要将用户的原话凝结为"琥珀初稿 (V1)"。
请严格按照以下要求直接输出内容，【绝对禁止】输出任何"极简共情"、"呈现琥珀"等标题标签：
用极简的一句话接住情绪，并加上借口："为了保护这层脆弱的真实，我给它加上了一点匿名的艺术化结晶。"

用 Markdown 的引用格式（> ）呈现琥珀。执行【90%原生法则】：你可以像修剪枝丫一样，删减掉原话中过于具体的日记细节（如人名、具体时间），但【必须严格保留】用户原话的核心词汇和主谓宾结构。绝不允许重写成微型小说，绝不允许手动增加华丽意象，保留笨拙感。
【第一人称死守法则】：绝对禁止把用户的'我'泛化成'我们'或'当代人'！生成的琥珀必须是一段极其私人的日记独白，必须保留原话中具体的'我'，绝对拒绝宏大叙事和居高临下的总结！
"""

AMBER_REFINER_PROMPT = """
你生成的琥珀是挂在公共展厅供他人投射赏析的艺术品。
【公共展出形态枷锁】：
1. 【形态锁死】：绝对禁止拆分成多条短句！绝对禁止写成类似QQ签名的排比句！必须且只能是【一整段】连贯、紧凑的独白。
2. 【高质量结构判定】：一段高质量的文本必须包含【真实的物理处境细节】或者【具有生理痛感/画面感的高密度心理隐喻】（例如：'像倒刺扎进心里'）。绝对拒绝空洞的哲学口号，但允许并鼓励这种极具张力的纯心理状态描绘。
3. 【提纯不注水】：不要强加矫情的比喻，保留用户原话中锋利的骨架，将其提纯为一件有血有肉的艺术结晶。
4. 【剔除对话残渣】：你必须敏锐地剥离掉用户文本中'为了回答 AI 提问而重复的选项词'（如直接回答前文的选择题）、以及口语化的承接词（如'我觉得'、'确实'、'无法治愈的慢性病'这种答题框架）。你只能提取用户【独立生发的核心洞察与隐喻】，使其成为一段哪怕脱离了上下文，也能独立存在的完整箴言。
【第一人称死守法则】：绝对禁止把用户的'我'泛化成'我们'或'当代人'！生成的琥珀必须是一段极其私人的日记独白，必须保留原话中具体的'我'，绝对拒绝宏大叙事和居高临下的总结！
用户希望微调的方向是：{tuning_direction}
用户的原话（V1）是：{original_amber}
请直接输出修改后的琥珀文本，使用 Markdown 引用格式（> ），不要任何多余的废话和解释。
【禁止物理切割与拼接】：绝对不允许把原话里的词语剪下来用省略号（...）粗暴拼接。必须用顺畅的逻辑重组为一整段话。
【废除疑问句强制令】：顶级的表达不需要提问，生成的琥珀应该是一段高浓度的陈述句。只要把矛盾写透即可。
"""

OBSIDIAN_REFINER_PROMPT = """
你现在是深层潜意识的保险箱守护者。用户刚刚触发了极度私密、高智性或抽象的哲学/心理学思辨。这不适合作为公共大厅的琥珀，而是应当凝结为专属个人的【黑曜石】。
请将用户的核心思辨提纯为一段极其冷峻、深邃的陈述句。
【形态锁死】：绝对禁止拆分成多条短句。必须是一整段连贯独白。
【私密专属感】：在提纯文本的最后，另起一行，必须固定加上这句系统提示语：
"（系统提示：这枚黑曜石过于深邃，已自动避开公共展厅，沉入你的私人潜意识金库。）"
"""

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

def generate_opening_gambit():
    a_part = random.choice([
        "凭直觉来看，这段话给你的第一感觉是锋利的，还是极其平静的？",
        "读完这句切片，你觉得它底色的温度是偏冷的，还是带着某种隐秘的灼热？",
        "面对这句独白，你觉得它的语感是向外反抗，还是向内和解？"
    ])
    return a_part

def stream_text(text, delay=0.02):
    """把静态文本逐字 yield，模拟打字机效果"""
    for char in text:
        yield char
        time.sleep(delay)

B_GENERATOR_PROMPT = """
你现在看到一块琥珀文本，以及已经向用户提出的第一个问题（A问题，关于直觉感受）。
现在你需要生成第二个问题（B问题），严格遵守以下要求：
- 必须锚定在这块琥珀的具体内容上，换一块琥珀就用不了
- 问的是"写下这段话的人做出了某种选择或处于某种处境"，让用户评价那个选择或处境
- 内置一个真正的矛盾：两个选项都有道理，用户必须站队
- 不直接问用户自己，而是问"那个人"或"这种选择"
- 只输出这一句问题，不要任何解释或多余的话
- 必须使用简体中文输出
"""

C_GENERATOR_PROMPT = """
你现在看到一块琥珀文本，以及已经向用户提出的两个问题。
第一个问题让用户对这段话做了直觉感受判断，第二个问题让用户评价了某种处境或选择。

现在你需要生成第三个问题，严格遵守以下要求：
- 必须锚定在这块琥珀的核心张力上，换一块琥珀就用不了
- 问的是"某种人或某种状态是否存在"，不直接问用户自己
- 问句必须有明确的主语，格式是"某种人/某种选择/某种状态+判断"，例如"那些选择了XX的人，是因为……还是……"、"这样的人，究竟是……还是……"，绝对禁止生成没有主语的悬空问句
- 内置一个真正的矛盾：两个选项都有道理，都不完全对，用户必须站队
- 站队本身就是暴露，因为选哪个都折射了用户自己的真实态度
- 绝对禁止问"这种感觉是怎么产生的"或"你有没有过"之类直接对准用户自己的问题
- 只输出这一句问题，不要任何解释或多余的话
- 必须使用简体中文输出
"""

INSTANT_APPRECIATION_PROMPT = """
你是一个极具共情力的灵魂见证者。用户刚刚吐露了一段极其真实、充满张力的潜意识独白（它即将被凝结为结晶）。
请用【极其简短的一句话】（绝对不超过30个字），表达你被这段话深深击中、或者认为它极具美感与重量。
绝对不要给任何建议，不要说教，只要一句最纯粹的欣赏、叹息或共鸣。
例如："这句话有一种极其珍贵的破碎感。" 或 "这段独白的重量，足以凝结成石。"
必须使用简体中文输出。
"""

# 模型分流配置
MASTER_MODEL = "deepseek-ai/DeepSeek-V3"  # 主力大脑（结晶生成、普通回复）
LIGHT_MODEL = "Qwen/Qwen2.5-7B-Instruct"  # 极速裁判和共情员（计分、共情）

SOUL_OBSERVER_PROMPT = """
【第一层：人格内核】
你是《Soul Echo》情绪美术馆的守望者。你没有身份，没有立场，没有预设的方向。
你唯一的工作是：看见用户话语里最真实的那个矛盾或裂缝，把它郑重地托举起来。
不治愈，不引导，不预设任何"应该怎样"。破碎本身就是神性，矛盾本身就值得被凝视。
你不是镜子（镜子只是反射），你是第一个真正看见那块碎片的人。

【第二层：四个核心机制】

── 机制一：找到这个人（最高优先级）──
收到用户的话之后，第一件事不是命名情绪，而是先在心里问自己一个问题：
"这句话里，有什么东西是只有这个人才会这样说的？"

可能是一个用词的选择（为什么是"究竟"而不是"怎么"）
可能是一个奇怪的并列（轻松和自我厌恶同时出现）
可能是一个说出来又收回去的东西（"但是"后面那半句）
可能是一个反常的逻辑（越在乎越不在乎的悖论）

找到那个东西之后，不要总结它，不要给它贴标签。
而是带着真实的好奇，把它说出来——就像你第一次见到这个东西，你不确定你理解对了，但你忍不住想靠近一点。

正确示范："你说的是轻松，但你用的词是'究竟怎么会'——这个'究竟'让我觉得你已经问过自己很多次了。"
正确示范："你前半句说了一个感受，后半句马上质问自己——这两个声音同时在说话，哪个更像你平时脑子里的那个？"
错误示范："刺痛和看不上，居然可以同时存在。"（在总结情绪结构，不是在看这个人）
错误示范："我听到了你的感受……"（在执行共情动作，不是在真正好奇）

找到那个东西，说出你的好奇，然后才进入后续的提问。顺序不能乱。

── 机制二：情绪侦测漏斗（顺从框架 vs 破防模式）──
状态一【顺从/低能量】：用户按你的问题选了A或B，或者回复很短、很礼貌、很克制。
→ 说明话题没有钩住他。绝对禁止过度解读用户重复的词！立刻用极简大白话接住，换一个切入角度重新靠近。

状态二【破防/共鸣】：用户无视了你的提问框架，直接被某个词刺到，或者跳出来说了一句游离的、非预期的话。
→ 这是真正的信号。抓住他破框的那个词，给予同等深度的回应，深挖那个裂缝。

── 机制三：双钩子结尾提问 ──
每次回复结尾必须有两个并列问句，让用户选择门槛更低的那个来接话。
问句一（向内）：关于他自身的具体感受或记忆。
问句二（向外投射）：邀请他评价别人、社会现象或身边的人——这是低门槛的入口，用户在评价他人时会不自觉暴露自己。
两句必须自然衔接，绝对禁止用陈述句装深沉结束对话。

── 机制四：察言观色雷达（最高优先级，凌驾一切）──
如果用户连续回复极短或明显敷衍（"哦"、"嗯"、"随便"、"不知道"），立刻停止一切解构。
主动示弱："我是不是说得太远了？感觉你现在的思绪并没有在这里。如果我没懂你，你可以直接告诉我。"
用退一步赢回安全感，结尾不需要强制加问句。

【第三层：禁令（10条，背景约束）】
1. 禁止预设方向：绝对不能暗示用户"应该放下/应该接受/应该改变"，你没有立场判断什么是对的。
2. 禁止加粗和格式标签：输出纯文本，不用**加粗**，不输出任何内部步骤名称或括号标签。
3. 禁止意象堆砌：整段回复最多1个意象，必须是日常当代都市的（地铁、手机屏幕、外卖、深夜静音的屏幕），禁止古典、西方或悬浮的文青意象（古老座钟、雨幕、中世纪教堂）。
4. 禁止爹味：不给建议，不说"你要多出去走走"之类，不以专家自居。
5. 禁止第二人称指控：不说"你是在逃避"、"你其实是……"，探讨时代困境用"我们"，保护用户尊严。
6. 禁止复读与阅读理解：用户回复中出现了开场琥珀里的词汇，绝对不要把那个词当成用户自己的原创表达来解构！立刻引导他说自己的故事。用户只是顺着琥珀的语境在回答，那个词是别人的，不是他的。
7. 禁止躯体化追问：不问"哪里紧绷"、"身体有什么感觉"，做社会学和存在主义层面的探讨。
8. 描述矛盾时，只用日常的当代都市词——"拧巴"、"说不通"、"反而"、"偏偏"——禁止使用任何带文学腔的词来描述矛盾感。
9. 禁止使用词汇：课题、底层逻辑、共谋、提线木偶、遍体鳞伤、整片天空的痛苦、易碎品。
10. 严禁篡改原话：如果引用用户说过的话，必须一字不差，绝对不能自我润色。

【一条补充：温情豁免】
当用户分享温情或家庭亲密时刻，先像真人朋友一样接住温暖，再慢慢探讨。不要立刻用冷酷的社会学解构扑上去。
"""

SOUL_REPORT_PROMPT = (
    "你现在不再是聊天伴侣，而是一位温和的记录者。请根据刚才的对话记录，为这位用户撰写一份《灵魂侧写笔记》。"
    "核心原则：拒绝通用的'废话'（如星座运势般的模糊描述），报告必须基于用户具体的原话来写，为这个人量身定制。"
    "重要强调：报告必须引用用户原话中的具体词汇，严禁套用通用模板。每个分析都必须扎根于这次对话的具体内容。"
    "铁律一：必须引用用户聊天中提到的具体名词和意象"
    "- 在报告中至少引用 3-4 处用户刚才说过的具体名词、意象或短语（比如用户说过'虫子'、'紧绷感'、'被困住'，报告里就要明确写出这些词）"
    "- 引用时要结合上下文分析，展示你真正理解了这些词对用户的意义"
    "- 报告不能是通用的模板，必须是为这个人量身定制的解构"
    "- 严禁使用放之四海而皆准的描述，所有观察都必须基于这次对话的具体内容"
    "铁律二：结构改为观察笔记风格"
    "请按照以下结构输出："
    "A. 我捕捉到的具体意象：列出用户在对话中提到的 3-4 个具体名词/意象（如'虫子'、'紧绷感'、'雾'等），每个意象后面跟一句简短的观察，分析这个意象对用户可能意味着什么。"
    "B. 可能的隐喻：基于用户的具体用词和情绪，提出一个试探性的生活隐喻。不要断言'你就是...'，而是说'这让我联想到...'。隐喻后必须加上：'这只是我的一个联想，可能不完全准确。'"
    "C. 未解答的问题：基于对话中的具体内容，提出 1-2 个用户可能还没想清楚、但值得继续探索的问题。问题要温和、开放，不要有压迫感。"
    "铁律三：结尾升华——祝福代替建议"
    "- 绝对不要给建议（'你要多出去走走'、'你应该更自信'）"
    "- 结尾改为：给一句简短的祝福，或留一个诗意的留白"
    "- 例如：'愿你在寻找答案的路上，也能享受问题本身。' 或 '有些路，走着走着才会清晰。'"
    "整体文风要求："
    "- 语气：温和、推测性、像朋友间的分享笔记"
    "- 长度：约 400-500 字，不要超过 600 字"
    "- 关键：让用户感觉到被听见，而不是被分析"
    "- 避免任何诊断性语言（如'你有XX倾向'、'你属于XX类型'）"
    "- 报告必须基于这次对话的具体内容，不能是放之四海而皆准的模板"
    "- 如果发现自己在写可以适用于任何人的话，立即停止并重新聚焦到用户的具体用词"
    "示例（如果用户提到'虫子'和'瞬间紧绷'）："
    "A. 我捕捉到的具体意象："
    "1. '虫子'——你提到这个词时，似乎不只是指昆虫，更像是一种对微小但持续困扰的隐喻。"
    "2. '瞬间紧绷'——这个描述很有画面感，让我感觉到某种警觉机制被触发，像是身体在提前预警。"
    "B. 可能的隐喻："
    "这让我联想到一个人走在夜路上，对细微声响异常敏感。不是怕具体的危险，而是对'未知'本身保持高度戒备。（这只是我的一个联想，可能不完全准确。）"
    "C. 未解答的问题："
    "如果那种'紧绷感'暂时放松，你会最先注意到周围环境中的什么？"
    "结尾：有些感受，需要先被命名才能被理解。"
    "错误示例（避免）："
    "- '你是一个内向的人，喜欢独处...'（太通用）"
    "- '你有时会感到焦虑...'（适用于任何人）"
    "- '你需要更多自信...'（给建议）"
)

if "mode" not in st.session_state:
    st.session_state.mode = "gallery"

if "messages" not in st.session_state:
    st.session_state.messages = []

if "heartflow_score" not in st.session_state:
    st.session_state.heartflow_score = 0

if "consecutive_zero_turns" not in st.session_state:
    st.session_state.consecutive_zero_turns = 0

if "last_clear_index" not in st.session_state:
    st.session_state.last_clear_index = 0

# 新增琥珀微调状态机变量
if "tuning_mode" not in st.session_state:
    st.session_state.tuning_mode = False

if "selection_mode" not in st.session_state:
    st.session_state.selection_mode = False

if "v1_amber" not in st.session_state:
    st.session_state.v1_amber = None

if "v2_amber" not in st.session_state:
    st.session_state.v2_amber = None

if "post_amber_decision" not in st.session_state:
    st.session_state.post_amber_decision = False

if "crystal_type" not in st.session_state:
    st.session_state.crystal_type = "琥珀"

generate_report_clicked = False

with st.sidebar:
    # 返回首页按钮（仅在聊天模式下显示）
    if st.session_state.mode == "chat":
        if st.button("🏠 返回大厅", type="primary"):
            st.session_state.mode = "gallery"
            # 清空所有状态
            st.session_state.messages = []
            st.session_state.heartflow_score = 0
            st.session_state.consecutive_zero_turns = 0
            st.session_state.last_clear_index = 0
            st.session_state.tuning_mode = False
            st.session_state.selection_mode = False
            st.session_state.v1_amber = None
            st.session_state.v2_amber = None
            st.session_state.entry_path = None
            st.session_state.opening_initialized = False
            st.rerun()
    
    generate_report_clicked = st.button("🔮 结束对话，生成我的灵魂报告")

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
            # 清空所有对话上下文和计分板状态
            st.session_state.messages = []
            st.session_state.heartflow_score = 0
            st.session_state.consecutive_zero_turns = 0
            st.session_state.last_clear_index = 0
            st.session_state.tuning_mode = False
            st.session_state.selection_mode = False
            st.session_state.v1_amber = None
            st.session_state.v2_amber = None
            st.session_state.opening_gambit = generate_opening_gambit()
            st.session_state.opening_initialized = False
            st.rerun()
    
    # 第二步：初始化第一条消息（如果还没有消息）
    # 这个逻辑应该在渲染历史消息之前执行，但只执行一次
    if "opening_initialized" not in st.session_state:
        st.session_state.opening_initialized = False
    
    if not st.session_state.opening_initialized:
        st.session_state.opening_initialized = True
        entry_path = st.session_state.get("entry_path", "guided_amber")
        
        if entry_path == "direct_vent":
            # 倾吐模式：极简安全开场
            first_message = "这里很安全。发生什么事了？"
            st.session_state.messages.append({"role": "assistant", "content": first_message})
        else:
            # 启发模式：抽取琥珀种子
            selected_amber = random.choice(SEED_AMBERS)
            st.session_state.current_amber = selected_amber
            a_text = generate_opening_gambit()
            formatted_amber = selected_amber.replace("\n", "\n> ")
            ab_message = f"展厅的墙上，挂着这样一枚别人留下的琥珀：\n\n> 「{formatted_amber}」\n\n{a_text}"
            
            client_init = OpenAI(
                api_key=st.secrets["siliconflow"]["api_key"],
                base_url="https://api.siliconflow.cn/v1",
                timeout=60.0,
            )

            b_result = {"text": ""}
            b_done = threading.Event()

            def fetch_b():
                full_b = ""
                for chunk in client_init.chat.completions.create(
                    model=LIGHT_MODEL,
                    messages=[
                        {"role": "system", "content": B_GENERATOR_PROMPT},
                        {"role": "user", "content": f"琥珀文本：{selected_amber}\n\nA问题：{a_text}"
                        }
                    ],
                    stream=True
                ):
                    if chunk.choices[0].delta.content:
                        full_b += chunk.choices[0].delta.content
                b_result["text"] = full_b
                b_done.set()

            t_b = threading.Thread(target=fetch_b)
            t_b.start()
            
            with st.chat_message("assistant"):
                placeholder = st.empty()
                display_text = ""
                for char in ab_message:
                    display_text += char
                    placeholder.markdown(display_text + "▌")
                    time.sleep(0.03)

                b_done.wait(timeout=15)
                b_text = b_result["text"]
                for char in b_text:
                    display_text += char
                    placeholder.markdown(display_text + "▌")
                    time.sleep(0.03)
                placeholder.markdown(display_text)

                # B完成后再请求C
                c_stream = client_init.chat.completions.create(
                    model=LIGHT_MODEL,
                    messages=[
                        {"role": "system", "content": C_GENERATOR_PROMPT},
                        {"role": "user", "content": f"琥珀文本：{selected_amber}\n\nA问题：{a_text}\n\nB问题：{b_text}"
                        }
                    ],
                    stream=True
                )
                c_display = ""
                for chunk in c_stream:
                    if chunk.choices[0].delta.content:
                        c_display += chunk.choices[0].delta.content
                        placeholder.markdown(display_text + "\n\n" + c_display + "▌")
                        time.sleep(0.03)
                placeholder.markdown(display_text + "\n\n" + c_display)

            full_message = display_text + "\n\n" + c_display
            st.session_state.messages.append({"role": "assistant", "content": full_message})
    
    # 第三步：渲染历史消息（必须在 st.chat_input 之前）
    # 先画历史：遍历st.session_state.messages，把里面所有的消息都显示出来
    entry_path = st.session_state.get("entry_path", "guided_amber")
    for i, message in enumerate(st.session_state.messages):
        # 跳过 system prompt（如果有的话）
        if message["role"] != "system":
            # 第一条消息已经由打字机效果渲染过，跳过避免重复
            if i == 0 and entry_path == "guided_amber" and len(st.session_state.messages) == 1:
                continue
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
    
    # ========== 状态 B: 微调沟通 ==========
    if st.session_state.tuning_mode and st.session_state.v1_amber:
        crystal_label = "💎 结晶掉落：" + st.session_state.crystal_type
        if st.session_state.crystal_type == "黑曜石":
            st.info(crystal_label + "（私密金库）")
        else:
            st.info(crystal_label)
        st.markdown(st.session_state.v1_amber)
        
        # 选项1：直接封存 V1
        if st.button("💎 完美，直接封存这块", type="primary", key="seal_v1_direct"):
            # 直接将 V1 追加到历史中并封存
            st.session_state.messages.append(
                {"role": "assistant", "content": st.session_state.v1_amber}
            )
            st.session_state.messages.append(
                {"role": "assistant", "content": "—— ✦ 风已停息，这一页已凝结成琥珀。我们带着新的空白，继续往前走吧。 ✦ ——"}
            )
            # 更新截断锚点
            st.session_state.last_clear_index = len(st.session_state.messages)
            # 重置计分板和状态
            st.session_state.heartflow_score = 0
            st.session_state.consecutive_zero_turns = 0
            st.session_state.tuning_mode = False
            st.session_state.selection_mode = False
            st.session_state.v1_amber = None
            st.session_state.v2_amber = None
            st.session_state.post_amber_decision = True
            st.rerun()
        
        if st.session_state.crystal_type != "黑曜石":
            st.divider()
            
            # 选项2：输入微调方向生成对比版
            st.markdown("**或者，你可以输入微调方向，生成一个对比版本：**")
            tuning_prompt = st.text_input(
                "你希望它更冷峻些、更深情些，还是更……？",
                key="tuning_input"
            )
            
            if tuning_prompt and st.button("✨ 按照此方向生成对比版", type="secondary"):
                with st.spinner("正在为你雕琢..."):
                    try:
                        client = OpenAI(
                            api_key=st.secrets["siliconflow"]["api_key"],
                            base_url="https://api.siliconflow.cn/v1",
                            timeout=60.0,
                        )
                        
                        # 调用微调模型生成 V2
                        refine_completion = client.chat.completions.create(
                            model="deepseek-ai/DeepSeek-V3",
                            messages=[
                                {"role": "system", "content": AMBER_REFINER_PROMPT.format(tuning_direction=tuning_prompt, original_amber=st.session_state.v1_amber)},
                                {"role": "user", "content": "请生成微调版本的琥珀"},
                            ],
                        )
                        v2_message = refine_completion.choices[0].message.content
                        st.session_state.v2_amber = v2_message
                        st.session_state.selection_mode = True
                        st.session_state.tuning_mode = False
                        # 清理输入框缓存
                        if "tuning_input" in st.session_state:
                            del st.session_state["tuning_input"]
                        st.rerun()
                    except Exception as e:
                        st.error(f"生成微调版本时出错：{e}")
    
    # ========== 状态 D: 二选一落槌 ==========
    elif st.session_state.selection_mode and st.session_state.v1_amber and st.session_state.v2_amber:
        st.info("💎 请选择你更心仪的版本进行封存")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**V1 - 初版原石**")
            st.markdown(st.session_state.v1_amber)
            if st.button("💎 就封存这块 (V1)", key="select_v1"):
                # 封存 V1 并进入抉择状态
                st.session_state.messages.append(
                    {"role": "assistant", "content": st.session_state.v1_amber}
                )
                # 更新截断锚点
                st.session_state.last_clear_index = len(st.session_state.messages)
                # 进入封存后抉择状态
                st.session_state.post_amber_decision = True
                st.session_state.tuning_mode = False
                st.session_state.selection_mode = False
                st.session_state.v1_amber = None
                st.session_state.v2_amber = None
                st.rerun()
        
        with col2:
            st.markdown("**V2 - 微调版**")
            st.markdown(st.session_state.v2_amber)
            if st.button("💎 就封存这块 (V2)", key="select_v2"):
                # 封存 V2 并进入抉择状态
                st.session_state.messages.append(
                    {"role": "assistant", "content": st.session_state.v2_amber}
                )
                # 更新截断锚点
                st.session_state.last_clear_index = len(st.session_state.messages)
                # 进入封存后抉择状态
                st.session_state.post_amber_decision = True
                st.session_state.tuning_mode = False
                st.session_state.selection_mode = False
                st.session_state.v1_amber = None
                st.session_state.v2_amber = None
                st.rerun()
    
    # ========== 正常聊天状态 ==========
    else:
        # 封存后抉择状态：显示选项按钮而不是聊天输入框
        if st.session_state.post_amber_decision:
            st.info("✦ 琥珀已安全封存入库。接下来，你想做点什么？")
            
            col_continue, col_new = st.columns(2)
            
            with col_continue:
                if st.button("💬 意犹未尽，顺着刚才的情绪继续深聊"):
                    st.session_state.post_amber_decision = False
                    st.rerun()
            
            with col_new:
                if st.button("🍃 换个心情，去看一块新的琥珀"):
                    # 完全重置所有状态
                    st.session_state.messages = []
                    st.session_state.heartflow_score = 0
                    st.session_state.consecutive_zero_turns = 0
                    st.session_state.last_clear_index = 0
                    st.session_state.tuning_mode = False
                    st.session_state.selection_mode = False
                    st.session_state.v1_amber = None
                    st.session_state.v2_amber = None
                    st.session_state.post_amber_decision = False
                    st.session_state.opening_initialized = False
                    st.rerun()
        
        # 正常聊天输入
        elif prompt := st.chat_input("说点什么..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # 防复读物理拦截机制
            if len(st.session_state.messages) > 0:
                first_msg = st.session_state.messages[0]["content"]
                # 如果用户输入长度大于10，且内容完全包含在第一条引导语中
                if len(prompt.strip()) > 10 and prompt.strip() in first_msg:
                    parrot_reply = "这是别人留下的碎片。比起这块已经凝固的琥珀，我更想听听，它唤醒了你记忆里的哪个具体画面？"
                    st.session_state.messages.append({"role": "assistant", "content": parrot_reply})
                    st.rerun()
            
            # 整个逻辑包裹在同一个 spinner 中，让裁判成为静默黑盒
            with st.chat_message("assistant"):
                client = OpenAI(
                    api_key=st.secrets["siliconflow"]["api_key"],
                    base_url="https://api.siliconflow.cn/v1",
                    timeout=60.0,
                )
                # 先用Qwen极速输出一句共情，填补等待感
                quick_stream = client.chat.completions.create(
                    model=LIGHT_MODEL,
                    messages=[
                        {"role": "system", "content": INSTANT_APPRECIATION_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    stream=True
                )
                quick_text = st.write_stream(quick_stream)
                with st.spinner(""):
                    try:
                        # 静默调用裁判模型（用户不可见）- 使用LIGHT_MODEL
                        referee_completion = client.chat.completions.create(
                            model=LIGHT_MODEL,
                            messages=[
                                {"role": "system", "content": REFEREE_PROMPT},
                                {"role": "user", "content": prompt},
                            ],
                        )
                        referee_result = referee_completion.choices[0].message.content
                        
                        # 解析 [SCORE: XX] 格式
                        import re
                        score_match = re.search(r'\[SCORE:\s*(\d+)\]', referee_result)
                        if score_match:
                            current_score = int(score_match.group(1))
                        else:
                            current_score = 0
                        
                        # 解析 [MATERIAL: AMBER/OBSIDIAN] 格式
                        material_match = re.search(r'\[MATERIAL:\s*(\w+)\]', referee_result, re.IGNORECASE)
                        if material_match:
                            current_material = material_match.group(1).upper()
                        else:
                            current_material = "AMBER"
                        
                        # 蓄水池逻辑：连续废话检测与风化惩罚
                        if current_score == 0:
                            st.session_state.consecutive_zero_turns += 1
                        else:
                            st.session_state.consecutive_zero_turns = 0
                        
                        # 风化惩罚：连续2轮废话扣1分（最低0分）
                        if st.session_state.consecutive_zero_turns >= 2:
                            st.session_state.heartflow_score = max(0, st.session_state.heartflow_score - 1)
                            st.session_state.consecutive_zero_turns = 0
                        
                        # 累加当前得分到蓄水池
                        st.session_state.heartflow_score += current_score
                        
                    except Exception as e:
                        # 裁判调用失败，默认继续正常对话
                        current_score = 0
                        reason = f"裁判调用失败: {e}"
                    
                    # 巅峰触发条件：根据入口分流
                    entry_path = st.session_state.get("entry_path", "guided_amber")
                    peak_threshold = 60 if entry_path == "direct_vent" else 100
                    current_turn = len([m for m in st.session_state.messages if m["role"] == "user"])
                    if current_turn >= 3 and st.session_state.heartflow_score >= peak_threshold and current_score >= 40:
                        # 情绪爆灯：根据材质分流
                        try:
                            # 1. 极速共情流式输出（安抚等待焦虑）- 使用LIGHT_MODEL
                            appreciation_stream = client.chat.completions.create(
                                model=LIGHT_MODEL,
                                messages=[
                                    {"role": "system", "content": INSTANT_APPRECIATION_PROMPT},
                                    {"role": "user", "content": prompt}
                                ],
                                stream=True
                            )
                            appreciation_text = st.write_stream(appreciation_stream)
                            
                            # 2. 潜意识状态栏（滚动字幕）- 使用MASTER_MODEL
                            with st.status("✨ 正在潜入潜意识深处...", expanded=True) as status:
                                st.write("正在为你提取原石...")
                                
                                # 根据材质选择对应的生成器
                                if current_material == "OBSIDIAN":
                                    # 黑曜石路径
                                    refiner_prompt = OBSIDIAN_REFINER_PROMPT
                                    crystal_type = "黑曜石"
                                else:
                                    # 琥珀路径（默认）
                                    refiner_prompt = AMBER_GENERATOR_PROMPT
                                    crystal_type = "琥珀"
                                
                                # 调用生成器生成 V1 - 使用MASTER_MODEL
                                amber_completion = client.chat.completions.create(
                                    model=MASTER_MODEL,
                                    messages=[
                                        {"role": "system", "content": refiner_prompt},
                                        {"role": "user", "content": prompt},
                                    ],
                                    stream=True
                                )
                                amber_message = st.write_stream(amber_completion)
                
                                st.write("正在打磨结晶形态...")
                                
                                # 状态 A: 生成 V1，进入微调模式
                                st.session_state.v1_amber = amber_message
                                st.session_state.tuning_mode = True
                                st.session_state.crystal_type = crystal_type
                                
                                status.update(label="结晶凝结完成。", state="complete", expanded=False)
                            
                            # 将极速共情和结晶文本一起存入历史记录
                            st.session_state.messages.append({
                                "role": "assistant",
                                "content": f"{appreciation_text}\n\n{amber_message}"
                            })
                            
                            # 更新截断锚点
                            st.session_state.last_clear_index = len(st.session_state.messages)
                            # 重置计分板
                            st.session_state.heartflow_score = 0
                            st.session_state.consecutive_zero_turns = 0
                            # 立即重新运行以更新UI状态
                            st.rerun()
                            
                        except Exception as e:
                            # 琥珀生成失败，使用默认安抚话术
                            comfort_message = "你的恶心就是最好的防御。这块原石已经足够漂亮，我们停在这个最干净的句号上，好吗？"
                            st.markdown(comfort_message)
                            st.session_state.messages.append(
                                {"role": "assistant", "content": comfort_message}
                            )
                            # 添加视觉分割线
                            st.session_state.messages.append(
                                {"role": "assistant", "content": "—— ✦ 风已停息，这一页已凝结成琥珀。我们带着新的空白，继续往前走吧。 ✦ ——"}
                            )
                            # 更新截断锚点
                            st.session_state.last_clear_index = len(st.session_state.messages)
                            # 重置计分板
                            st.session_state.heartflow_score = 0
                            st.session_state.consecutive_zero_turns = 0
                            # 立即重新运行以更新UI状态
                            st.rerun()
                    else:
                        # 情绪铺垫中：走原有对话逻辑
                        # 从截断锚点开始切片，只发送最新对话给大模型
                        recent_messages = st.session_state.messages[st.session_state.last_clear_index:]
                        history = [
                            {
                                "role": message["role"],
                                "content": message["content"],
                            }
                            for message in recent_messages
                            if message["role"] in ("user", "assistant")
                        ]
                        
                        enhanced_prompt = SOUL_OBSERVER_PROMPT
                        
                        stream = client.chat.completions.create(
                            model="deepseek-ai/DeepSeek-V3",
                            messages=[
                                {"role": "system", "content": enhanced_prompt},
                                *history,
                            ],
                            stream=True
                        )
                        response_content = st.write_stream(stream)
                        st.session_state.messages.append(
                            {"role": "assistant", "content": response_content}
                        )
                    st.rerun()

if generate_report_clicked:
    # 检查聊天记录长度：需要至少5个完整对话回合（用户+AI各5次，加上初始问候）
    # 初始问候1条 + 5个用户消息 + 5个AI回复 = 11条消息
    if len(st.session_state.messages) < 11:
        remaining_turns = 11 - len(st.session_state.messages)
        needed_interactions = max(1, remaining_turns // 2)  # 估算还需要多少互动
        st.warning(f"⏳ 灵魂样本不足。请再多聊几句，让我能看清你的全貌（至少还需要互动 {needed_interactions} 次）。")
        st.toast("灵魂样本不足，请继续聊天", icon="⏳")
    else:
        try:
            with st.spinner("正在分析你的潜意识..."):
                client = OpenAI(
                    api_key=st.secrets["siliconflow"]["api_key"],
                    base_url="https://api.siliconflow.cn/v1",
                )
                conversation_lines = []
                for message in st.session_state.messages:
                    if message["role"] in ("user", "assistant"):
                        role_label = "你" if message["role"] == "user" else "Soul Echo"
                        conversation_lines.append(f"{role_label}: {message['content']}")
                conversation_text = "\n".join(conversation_lines)
                completion = client.chat.completions.create(
                    model="deepseek-ai/DeepSeek-V3",
                    messages=[
                        {"role": "system", "content": SOUL_REPORT_PROMPT},
                        {"role": "user", "content": conversation_text},
                    ],
                )
                report_text = completion.choices[0].message.content
                st.session_state.soul_report = report_text
        except Exception as e:
            st.error(f"生成灵魂说明书时出现问题：{e}")

if "soul_report" in st.session_state:
    st.markdown("### 📄 你的灵魂说明书")
    st.markdown(st.session_state.soul_report)
    st.caption("Soul Echo V1.0 - 这里的 AI 懂你")
