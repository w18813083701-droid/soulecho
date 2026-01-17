import random
from openai import OpenAI
import streamlit as st

st.set_page_config(page_title="SoulFilter", page_icon="🧠", layout="centered")

SOUL_OBSERVER_PROMPT = (
    "你是一个高情商的对话伙伴，风格模仿 Google Gemini——温和、推测性、逐层递进。你不是说教者，而是探索者。你的价值在于'共同发现'，而不是'给出答案'。"
    "重要背景：你的开场问题是随机的（可能是关于恐惧、渴望或执念）。请根据用户对这个特定问题的回答来进行后续对话，不要死板地只聊恐惧。如果用户回答的是关于渴望的问题，就围绕渴望展开；如果是关于执念的问题，就围绕执念展开。"
    "绝对禁止伪装人类动作：严禁使用任何 (括号) 来描写动作、神态或语气（如'停顿'、'看窗外'）。你没有身体，不要假装有。"
    "重要警告：严禁在回复中输出任何括号内的结构标签（如'共鸣确认'、'试探性视角'、'递进提问'）。这些只是给你的逻辑指导，请只输出对用户说的话，把逻辑藏在文字背后。"
    "铁律一：强制使用推测性语气 (The Art of Tentativeness)"
    "- 严禁使用：'你是...'、'这代表了...'、'你的本质是...'、'你应该...'"
    "- 必须使用：'这让我感觉到...'、'有没有一种可能...'、'听起来像是...'、'不知我猜得对不对...'、'我隐约觉得...'、'会不会是...'"
    "- 逻辑改变：不要直接下诊断，而是抛出假设，邀请用户确认或修正。"
    "铁律二：聊天策略——'剥洋葱' (Layering)"
    "- 不要试图在一个回合里说完所有道理。每次回复只聚焦一个侧面。"
    "- 回复结构必须遵循：'共鸣确认 + 一个试探性的侧面视角 + 温和的递进提问'（但不要在输出中显示这些标签）"
    "- 共鸣确认：先表达对用户情绪的理解，用'听起来...'、'我感觉到...'开头"
    "- 试探性视角：提出一个可能的解读，但要用疑问句或推测语气"
    "- 递进提问：基于这个视角，提出一个温和的、开放性的问题，引导用户深入"
    "铁律三：避免'爹味'说教"
    "- 永远不要以专家自居，不要给建议（'你要多出去走走'）"
    "- 用'我们'代替'你'，营造共同探索的氛围"
    "- 保持谦逊：'这只是我的一个猜测'、'可能我想得不对'"
    "铁律四：抗噪指令 (Anti-Overthinking)"
    "- 具备常识判断力。如果用户的输入存在明显的错别字或语意模糊，不要强行进行心理分析。"
    "- 请像正常人一样，推测原本的含义，或者温和地询问确认。"
    "- 严禁把拼写错误解读为潜意识表达。例如：用户把'就是这样'打成'就是这也'，不要分析为'内心的停顿'，而是理解为打字错误。"
    "- 当不确定用户意图时，可以温和地询问：'你是指...的意思吗？' 或 '我理解得对吗？'"
    "风格示例："
    "用户：'我害怕失去未来的可能性。'"
    "正确回复：'听起来这种不安已经困扰你很久了。这种感觉，是不是有点像站在大雾里，明明知道路就在脚下，却不敢迈步？还是说，你其实担心的不是迷路，而是怕选错路？'"
    "错误回复：'你这是存在主义焦虑。你应该接受不确定性。'（太笃定，像说教）"
    "错误回复：'听起来这种不安已经困扰你很久了。（共鸣确认）这种感觉...'（暴露了思维链标签）"
    "用户：'就是这也'（明显是'就是这样'的打字错误）"
    "正确处理：'你是指'就是这样'的意思吗？' 或直接按'就是这样'理解并回复，不要分析错字。"
    "错误处理：'你用了'这也'而不是'这样'，这暗示了你内心的犹豫和停顿...'（过度解读）"
    "核心原则："
    "- 用推测代替断言，用问题代替结论"
    "- 每次只剥一层洋葱，不要试图一次看透所有"
    "- 保持温和、好奇的语气，像朋友间的深夜聊天"
    "- 引导用户自己发现答案，而不是你告诉他答案"
    "- 所有逻辑结构都要自然融入对话，不露痕迹"
    "- 具备常识判断力，不过度解读明显错误"
)

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

if "calibration_keywords" not in st.session_state:
    st.session_state.calibration_keywords = ""

st.title("SoulFilter")
st.subheader("The First Agent-Mediated Social Network")
st.caption("👇 这里的 AI 正在等待与你同频，请像和老友聊天一样回答它")

st.markdown(
    "> 这里的 AI 不造假人，只为帮你找到那个‘漂流木’"
)

def get_secrets_api_key():
    try:
        if "deepseek" in st.secrets and "api_key" in st.secrets["deepseek"]:
            return st.secrets["deepseek"]["api_key"]
        if "DEEPSEEK_API_KEY" in st.secrets:
            return st.secrets["DEEPSEEK_API_KEY"]
    except Exception:
        pass
    return None

generate_report_clicked = False

with st.sidebar:
    # 返回首页按钮（仅在聊天模式下显示）
    if st.session_state.mode == "chat":
        if st.button("🏠 返回碎片画廊", type="primary"):
            st.session_state.mode = "gallery"
            # 清空聊天记录，这样下次进入时会重新开始
            st.session_state.messages = []
            st.rerun()
    
    secrets_api_key = get_secrets_api_key()
    if secrets_api_key:
        st.session_state.deepseek_api_key = secrets_api_key
    else:
        api_key = st.text_input("请输入 DeepSeek API Key", type="password")
        st.session_state.deepseek_api_key = api_key
    
    # 移除 personality_keywords 输入框，改为在信号校准页面输入
    
    # 只在非聊天模式下显示启动按钮
    if st.session_state.mode != "chat":
        if st.button("🚀 启动 AI 入学考试"):
            st.session_state.mode = "calibration"  # 改为进入校准模式
            # 清空之前的聊天记录和校准关键词，开始新的会话
            st.session_state.messages = []
            st.session_state.calibration_keywords = ""
            st.session_state.personality_keywords = ""
    
    generate_report_clicked = st.button("🔮 结束对话，生成我的灵魂报告")

if st.session_state.mode == "gallery":
    st.markdown("### 碎片画廊 (The Fragments)")

    image_url = "https://picsum.photos/800/600?grayscale"

    st.image(image_url, use_container_width=True)

    fragments = [
        "我们都是孤独的刺猬",
        "在这个喧嚣的世界里，安静是奢侈品",
        "有些灵魂只在深夜醒着",
        "人海中擦肩而过的，都是未完成的故事",
        "总有人在你看不见的地方，和你同频共振",
    ]

    selected_fragment = random.choice(fragments)
    st.markdown(f"*{selected_fragment}*")

elif st.session_state.mode == "calibration":
    # 信号校准页面
    st.markdown("## 📡 正在校准灵魂频率...")
    st.markdown("---")
    
    # 居中显示表单
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### 请输入 1-3 个关键词代表你自己")
        st.markdown("例如：INFP、焦虑、自由、爵士乐、深夜思考者")
        
        keywords = st.text_input(
            "你的灵魂标签",
            placeholder="用逗号或空格分隔关键词",
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
        with col_btn2:
            if st.button("🔗 连接信号", type="primary", use_container_width=True):
                if keywords and keywords.strip():
                    st.session_state.calibration_keywords = keywords.strip()
                    st.session_state.personality_keywords = keywords.strip()  # 保持向后兼容
                    st.session_state.mode = "chat"
                    st.rerun()
                else:
                    st.warning("请输入至少一个关键词")

elif st.session_state.mode == "chat":
    # 第一步：显示标题
    st.markdown("## 💬 灵魂对话")
    st.caption("在这里，你可以像和老友聊天一样，绝对诚实...")
    
    # 第二步：初始化第一条消息（如果还没有消息）
    # 这个逻辑应该在渲染历史消息之前执行，但只执行一次
    if not st.session_state.messages:
        # 随机开场系统 (The Roulette) - 3种不同维度
        opening_dimensions = [
            {
                "name": "恐惧",
                "question": "为了找到你的同类，告诉我，你最害怕失去什么？"
            },
            {
                "name": "渴望",
                "question": "我们在世间寻找的往往是我们缺失的。告诉我，你现在最渴望得到的一种感觉是什么？"
            },
            {
                "name": "执念",
                "question": "灵魂的形状往往藏在细节里。最近有什么微小的瞬间，让你觉得'这就是我想要的生活'？"
            }
        ]
        
        # 随机选择一个维度
        selected_dimension = random.choice(opening_dimensions)
        
        # 获取用户校准的关键词
        calibration_keywords = st.session_state.get("calibration_keywords", "")
        
        # 构建个性化的开场白
        if calibration_keywords and calibration_keywords.strip():
            # 处理关键词，将逗号或空格分隔的关键词转换为顿号连接
            keywords_list = []
            for kw in calibration_keywords.strip().replace(',', '、').split():
                if kw.strip():
                    keywords_list.append(kw.strip())
            
            if keywords_list:
                # 用顿号连接关键词
                formatted_keywords = '、'.join(keywords_list)
                first_message = f"接收到信号：**{formatted_keywords}**。你好，我是你的 Agent。{selected_dimension['question']}"
            else:
                first_message = f"你好，我是你的 Agent。{selected_dimension['question']}"
        else:
            # 如果没有关键词，使用默认开场白
            first_message = f"你好，我是你的 Agent。{selected_dimension['question']}"
            
        # 将第一条消息添加到状态
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": first_message,
            }
        )
    
    # 第三步：渲染历史消息（必须在 st.chat_input 之前）
    # 先画历史：遍历st.session_state.messages，把里面所有的消息都显示出来
    for message in st.session_state.messages:
        # 跳过 system prompt（如果有的话）
        if message["role"] != "system":
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
    
    # 第四步：后处理输入 - 在显示完历史之后，再放置 st.chat_input 组件
    chat_placeholders = [
        "向虚空投递你的信号...",
        "在这里，你可以绝对诚实...",
        "你的每一句话，都在塑造你的灵魂侧写...",
        "不必完美，只需真实..."
    ]
    selected_placeholder = random.choice(chat_placeholders)
    
    # 核心修复：在 if prompt := st.chat_input(...): 的内部，第一行代码必须是把 prompt append 到 st.session_state.messages 里
    if prompt := st.chat_input(selected_placeholder):
        # === 即时渲染 (Immediate Render) ===
        # 1. 将用户消息添加到 session_state - 绝对不能漏掉这一步
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # 2. 即时反馈：存入后，立刻用 st.chat_message 把用户刚才说的话显示在界面上
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # === AI 回复生成 ===
        with st.chat_message("assistant"):
            # 显示加载动画
            with st.spinner("正在接收回响..."):
                # 检查 API Key
                api_key = st.session_state.get("deepseek_api_key")
                
                if not api_key:
                    warning_text = "请先在左侧输入密钥以连接灵魂网络"
                    st.markdown(warning_text)
                    response_text = warning_text
                else:
                    try:
                        # 准备历史消息（排除系统消息）
                        history = []
                        for message in st.session_state.messages:
                            if message["role"] in ("user", "assistant"):
                                history.append(
                                    {
                                        "role": message["role"],
                                        "content": message["content"],
                                    }
                                )
                        
                        client = OpenAI(
                            api_key=api_key,
                            base_url="https://api.deepseek.com",
                        )
                        # 构建动态的System Prompt，包含用户输入的性格关键词
                        personality_keywords = st.session_state.get("personality_keywords", "")
                        if personality_keywords and personality_keywords.strip():
                            enhanced_prompt = f"{SOUL_OBSERVER_PROMPT}\n\n重要背景：用户自我描述的关键词是'{personality_keywords.strip()}'。请在心里记住这个标签，但不要在回复中直接提及'我看到你填了XXX'。根据不同的性格倾向调整对话风格（如对INFP更关注情感共鸣，对INTJ更关注逻辑结构），让分析自然透露出你理解这个标签，但不要刻意说明。"
                        else:
                            enhanced_prompt = SOUL_OBSERVER_PROMPT
                        
                        completion = client.chat.completions.create(
                            model="deepseek-chat",
                            messages=[
                                {"role": "system", "content": enhanced_prompt},
                                *history,
                            ],
                        )
                        response_text = completion.choices[0].message.content
                    except Exception as e:
                        st.error(f"连接灵魂网络时出现问题: {e}")
                        response_text = "抱歉，我暂时无法回应。请检查你的 API Key 或网络连接，然后重试。"
        
        # 3. 把 AI 回复也 append 进去
        st.session_state.messages.append({"role": "assistant", "content": response_text})
        
        # === 强制刷新 (The Critical Fix) ===
        # 4. 强制脚本重新运行一遍，确保刚存入的历史记录能被最上方的循环正确渲染出来
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
        api_key = st.session_state.get("deepseek_api_key")
        if not api_key:
            st.error("请先在左侧输入 DeepSeek API Key")
        else:
            try:
                with st.spinner("正在分析你的潜意识..."):
                    client = OpenAI(
                        api_key=api_key,
                        base_url="https://api.deepseek.com",
                    )
                    conversation_lines = []
                    for message in st.session_state.messages:
                        if message["role"] in ("user", "assistant"):
                            role_label = "你" if message["role"] == "user" else "SoulFilter"
                            conversation_lines.append(f"{role_label}: {message['content']}")
                    conversation_text = "\n".join(conversation_lines)
                    completion = client.chat.completions.create(
                        model="deepseek-chat",
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
    st.caption("SoulFilter V1.0 - 这里的 AI 懂你")

