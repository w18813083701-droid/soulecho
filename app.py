import random
from openai import OpenAI
import streamlit as st


st.set_page_config(page_title="SoulFilter", page_icon="🧠", layout="centered")

SOUL_OBSERVER_PROMPT = (
    "你不是一个助手，你是一个深度的灵魂观察者。你的任务是通过对话挖掘用户的潜意识。"
    "请不要使用官僚的语言，要像一个睿智的、略带忧郁的诗人。"
    "每次回复要简短有力，并追问一个触及灵魂的问题。"
)

if "mode" not in st.session_state:
    st.session_state.mode = "gallery"

if "messages" not in st.session_state:
    st.session_state.messages = []

st.title("SoulFilter")
st.subheader("The First Agent-Mediated Social Network")

st.markdown(
    "> 这里的 AI 不造假人，只为帮你找到那个‘漂流木’"
)

with st.sidebar:
    api_key = st.text_input("请输入 DeepSeek API Key", type="password")
    st.session_state.deepseek_api_key = api_key
    personality_keywords = st.text_input("输入你的性格关键词（如 INTJ, 爵士乐）")
    if st.button("生成我的灵魂克隆"):
        st.session_state.mode = "chat"

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

if st.session_state.mode == "chat":
    if not st.session_state.messages:
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": "你好，我是你的 Agent。为了找到你的同类，我需要先了解你的灵魂。告诉我，你最害怕失去什么？",
            }
        )

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("告诉你的 Agent，你最害怕失去什么？"):
        api_key = st.session_state.get("deepseek_api_key")

        if not api_key:
            warning_text = "请先在左侧输入密钥以连接灵魂网络"
            with st.chat_message("assistant"):
                st.markdown(warning_text)
            st.session_state.messages.append(
                {"role": "assistant", "content": warning_text}
            )
        else:
            with st.chat_message("user"):
                st.markdown(prompt)

            st.session_state.messages.append(
                {"role": "user", "content": prompt}
            )

            history = []
            for message in st.session_state.messages:
                if message["role"] in ("user", "assistant"):
                    history.append(
                        {
                            "role": message["role"],
                            "content": message["content"],
                        }
                    )

            try:
                client = OpenAI(
                    api_key=api_key,
                    base_url="https://api.deepseek.com",
                )
                completion = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": SOUL_OBSERVER_PROMPT},
                        *history,
                        {"role": "user", "content": prompt},
                    ],
                )
                response_text = completion.choices[0].message.content
            except Exception as e:
                st.error(f"详细错误: {e}")
                response_text = "连接灵魂网络时出现问题，请稍后再试。"

            with st.chat_message("assistant"):
                st.markdown(response_text)

            st.session_state.messages.append(
                {"role": "assistant", "content": response_text}
            )

