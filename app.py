import streamlit as st
import os
import json
import networkx as nx
from pyvis.network import Network
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

st.set_page_config(page_title="Meaning Structure Analyzer", layout="wide")

# --- LLM 함수: 의미덩어리 추출 ---
def extract_meaning_chunks(text):
    prompt = f"""
    너의 목표는 주어진 텍스트에서 "긴장과 해소", "떡밥과 회수" 관계에 있는 의미덩어리(semantic chunks) 쌍들을 추출하는 거야. 
    각 의미덩어리에 대해:
      - id (0부터 정수)
      - summary (1줄) 
      - role (긴장/해소/떡밥/회수 중 택1)
      - link (연결되어 있는 다른 의미덩어리 id)

    '해소' 의미덩어리는 다른 의미덩어리를 가리키지 않아.
    '회수' 의미덩어리는 다른 의미덩어리를 가리키지 않아.
    '긴장' 의미덩어리는 하나 또는 여러 개의 '해소' 의미덩어리만 가리킬 수 있어.
    '떡밥' 의미덩어리는 하나 또는 여러 개의 '회수' 의미덩어리만 가리킬 수 있어.
    edge는 '긴장'--> '해소', '떡밥'-->'회수'인 연결만 존재해. 하나의 의미덩어리는 여러 개의 role을 가질 수 있어.  대신 각 role에 대해 edge로 대응되는 의미덩어리가 연결되어야 해.
    의미덩어리는 반드시 2개 이상이어야 해.

    출력은 JSON 배열로만.
    [
     {{
      "id": 0,
      "summary": "...",
      "role": "...",
      "link": [3]
     }}
    ]
    텍스트:
    {text}
    """

    response = client.chat.completions.create(
        #model="o3-2025-04-16",
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4
    )

    try:
        print(response.choices[0].message.content)
        return json.loads(response.choices[0].message.content)
    except:
        st.error("⚠️ JSON 파싱에 실패했습니다. 프롬프트를 조정하세요.")
        return []


# --- pyvis로 그래프 생성 ---
def create_graph(chunks):
    print(chunks)
    print(type(chunks))
    G = Network(height="600px", width="100%", directed=True)
    G.barnes_hut()
    
    chunks = list(chunks.values())[0]
    # 노드 추가
    for c in chunks:
        label = f"{c['id']}: {c['summary']}"
        color = "#FFD966" if c['role'] == "떡밥" else \
                "#FF6F61" if c['role'] == "회수" else \
                "#6FA8DC" if c['role'] == "긴장" else \
                "#93C47D" if c['role'] == "해소" else "#CCCCCC"

        G.add_node(c["id"], label=label, color=color)

    # 엣지 추가
    for c in chunks:
        if "link" in c:
            for nxt in c["link"]:
                G.add_edge(c["id"], nxt)

    return G


# --- Streamlit UI ---
st.title("🔮 Meaning Chunk Structure Analyzer (MVP)")
st.markdown("**텍스트 → 의미덩어리 → 구조 그래프 → 구조 분석 리포트** 자동 생성")

text_input = st.text_area("✨ 분석할 텍스트를 입력하세요", height=200)

if st.button("의미 구조 분석 시작"):
    if not text_input.strip():
        st.warning("텍스트를 입력하세요.")
        st.stop()

    with st.spinner("LLM으로 의미덩어리 추출 중..."):
        chunks = extract_meaning_chunks(text_input)

    st.subheader("📌 1. 의미덩어리(semantic chunk) 추출 결과")
    st.json(chunks)

    st.subheader("📌 2. 의미 관계 그래프")
    graph = create_graph(chunks)
    graph.save_graph("graph.html")
    st.components.v1.html(open("graph.html", "r").read(), height=650)

    # 의미 구조 요약 생성
    with st.spinner("구조 분석 보고서 생성 중..."):
        summary_prompt = f"""
        아래 의미덩어리 리스트를 기반으로 전체 구조적 특징을 분석해줘.

        - 핵심 의미덩어리 요약
        - 긴장-해소 구조 파악
        - 떡밥-회수 구조 여부
        - 구조적 리스크(모순, 구멍, 연결 약함 등)
        - 전체 스토리 아키텍처 평가 (10점 척도)

        의미덩어리:
        {chunks}
        """

        summary_resp = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": summary_prompt}],
            temperature=0.3
        ).choices[0].message.content

    st.subheader("📌 3. 구조 분석 리포트")
    st.write(summary_resp)

