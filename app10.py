import streamlit as st
import streamlit.components.v1 as components
import math

# 1. 페이지 설정
st.set_page_config(page_title="600m Subsea Battery Designer Pro", layout="wide")

st.markdown("""
    <style>
    .main > div { padding-top: 1.5rem; }
    iframe { border-radius: 10px; border: 1px solid #ddd; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚢 600m 대응 배터리 팩 설계")

# 2. 사이드바 (파라미터 제어)
with st.sidebar:
    st.header("⚙️ 설계 파라미터")
    
    with st.expander("🛠️ 하우징 & 구조", expanded=True):
        L = st.number_input("외경 길이 (L, mm)", value=6700)
        W = st.number_input("외경 폭 (W, mm)", value=1600)
        H = st.number_input("외경 높이 (H, mm)", value=637)
        wall_t = st.slider("벽 두께 (mm)", 10, 50, 25)
        foam_vol = st.slider("부력재 (L)", 0, 500, 0)
        
    with st.expander("⚡ 전기 및 배치", expanded=True):
        mod_l, mod_w, mod_h = 355, 165, 110
        mod_v_nom, mod_v_max, mod_ah, mod_kg = 44.4, 50.4, 60, 12 # 44.4V(Nom), 50.4V(Max)
        
        spacing_h = st.slider("수평 간격 (mm)", 10, 100, 30)
        spacing_v = st.slider("수직 간격 (mm)", 10, 100, 50)
        
        # 적층 단수 제한 로직
        internal_H = H - (2 * wall_t)
        margin_factor = 0.9 ** (1/3)
        avail_H = internal_H * margin_factor
        max_possible_layers = math.floor((avail_H + spacing_v) / (mod_h + spacing_v))
        max_possible_layers = max(1, max_possible_layers)
        
        layers = st.selectbox("적층 단수", range(1, max_possible_layers + 1), 
                              index=min(1, max_possible_layers - 1))

# 3. 데이터 계산 로직
n_l = math.floor((L * margin_factor) / (mod_l + spacing_h))
n_w = math.floor((W * margin_factor) / (mod_w + spacing_h))
used_mods = (n_l * n_w * layers) // 8 * 8

# [전기적 계산] 8S 구성 기준
pack_v_nom = mod_v_nom * 8 # 355.2V
pack_v_max = mod_v_max * 8 # 403.2V
total_energy_kwh = (used_mods * mod_v_nom * mod_ah / 1000)

# [물리적 계산]
pack_kg = 1500 + (wall_t * 10) + (used_mods * mod_kg) + (foam_vol * 0.5)
buoy_vol = (L * W * H / 1e9) + (foam_vol / 1000)
displaced_water_weight = buoy_vol * 1025
net_buoyancy = displaced_water_weight - pack_kg
cog_y = sum([(l - (layers-1)/2) * (mod_h + spacing_v) for l in range(layers)]) / layers if layers > 0 else 0

# 4. 메인 화면 구성
# 전압 정보가 포함된 상단 대시보드 (5개 컬럼으로 확장)
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("총 중량", f"{pack_kg:,} kg")
m2.metric("정격 전압 (Nom)", f"{pack_v_nom:.1f} V")
m3.metric("최대 전압 (Max)", f"{pack_v_max:.1f} V", delta=f"{pack_v_max - pack_v_nom:.1f}V ▲", delta_color="inverse")
m4.metric("총 에너지", f"{total_energy_kwh:.1f} kWh")
m5.metric("최종 부력", f"{net_buoyancy:.1f} kg", delta=f"{'부상' if net_buoyancy > 0 else '침하'}")

tab1, tab2 = st.tabs(["🎮 3D 인터랙티브 뷰어", "📋 설계 상세 리포트"])

with tab1:
    three_js_html = f"""
    <div id="container" style="width: 100%; height: 350px; background: #f8f9fa;"></div>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
    <script>
        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(75, 2, 0.1, 20000);
        const renderer = new THREE.WebGLRenderer({{antialias: true, alpha: true}});
        renderer.setSize(document.getElementById('container').clientWidth, 350);
        document.getElementById('container').appendChild(renderer.domElement);
        const controls = new THREE.OrbitControls(camera, renderer.domElement);

        const housing = new THREE.Mesh(new THREE.BoxGeometry({L}, {H}, {W}), 
                        new THREE.MeshStandardMaterial({{color: 0xaaaaaa, transparent: true, opacity: 0.15}}));
        scene.add(housing);

        const cog = new THREE.Mesh(new THREE.SphereGeometry(80), new THREE.MeshBasicMaterial({{color: 0xff0000}}));
        cog.position.set(0, {cog_y}, 0);
        scene.add(cog);

        let count = 0;
        for(let l=0; l<{layers}; l++) {{
            for(let i=0; i<{n_l}; i++) {{
                for(let j=0; j<{n_w}; j++) {{
                    if (count >= {used_mods}) break;
                    let color = (Math.floor(count/8) % 2 === 0) ? 0x27ae60 : 0x2ecc71;
                    const mod = new THREE.Mesh(new THREE.BoxGeometry({mod_l}, {mod_h}, {mod_w}), new THREE.MeshStandardMaterial({{color: color}}));
                    let ox = ({n_l} * ({mod_l} + {spacing_h})) / 2, oz = ({n_w} * ({mod_w} + {spacing_h})) / 2;
                    let py = (l - ({layers}-1)/2) * ({mod_h} + {spacing_v});
                    mod.position.set(i*({mod_l}+{spacing_h}) - ox + {mod_l}/2, py, j*({mod_w}+{spacing_h}) - oz + {mod_w}/2);
                    scene.add(mod);
                    count++;
                }}
            }}
        }}
        camera.position.set(6000, 3000, 6000);
        scene.add(new THREE.DirectionalLight(0xffffff, 1.2), new THREE.AmbientLight(0x404040));
        function animate() {{ requestAnimationFrame(animate); controls.update(); renderer.render(scene, camera); }}
        animate();
    </script>
    """
    components.html(three_js_html, height=370)

with tab2:
    r1, r2 = st.columns(2)
    r1.write("### 🔩 구조 및 부력 데이터")
    r1.table({"항목": ["하우징 가용 높이", "최대 적층 단수", "수직 무게 중심(CoG)", "배수량"], 
              "수치": [f"{avail_H:.1f} mm", f"{max_possible_layers} 단", f"{cog_y:.1f} mm", f"{displaced_water_weight:.1f} kg"]})
    
    r2.write("### ⚡ 상세 전기 데이터")
    r2.table({"항목": ["정격 전압 (Nominal)", "최대 전압 (Max)", "스트링 구성", "총 에너지 용량"], 
              "수치": [f"{pack_v_nom:.1f} V", f"{pack_v_max:.1f} V", f"8S {used_mods//8}P", f"{total_energy_kwh:.1f} kWh"]})