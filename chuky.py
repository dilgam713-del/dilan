import streamlit as st
import sqlite3
from datetime import datetime

# --- IMPORTS SEGUROS (NO CRASHEA) ---
scanner_ok = True
try:
    import av
    from pyzbar.pyzbar import decode
    from streamlit_webrtc import webrtc_streamer, VideoProcessorBase
except:
    scanner_ok = False

# --- CONFIG ---
st.set_page_config(page_title="ChukI'S FULL", layout="wide")

# --- ESTILO MODERNO ---
st.markdown("""
<style>
body { background-color: #0f172a; color: white; }
.stButton>button {
    border-radius: 10px;
    border: 2px solid #38bdf8;
    background-color: #1e293b;
    color: white;
}
.card {
    padding: 15px;
    border-radius: 15px;
    border: 2px solid #38bdf8;
    margin: 10px;
}
</style>
""", unsafe_allow_html=True)

# --- DB ---
conn = sqlite3.connect("chukis.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS productos(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT,
    precio REAL,
    stock INTEGER,
    codigo TEXT
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS ventas(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT,
    total REAL
)''')

conn.commit()

# --- SESSION ---
if "carrito" not in st.session_state:
    st.session_state.carrito = []

# --- MENÚ ---
menu = st.sidebar.selectbox("Menú", [
    "Inicio", "Inventario", "Escaneo PRO", "Ventas"
])

# --- INICIO ---
if menu == "Inicio":
    st.title("🛒 ChukI'S FULL")
    st.markdown('<div class="card">Sistema moderno con escaneo inteligente</div>', unsafe_allow_html=True)

# --- INVENTARIO ---
elif menu == "Inventario":
    st.header("📦 Inventario")

    nombre = st.text_input("Nombre")
    precio = st.number_input("Precio")
    stock = st.number_input("Stock")
    codigo = st.text_input("Código (barcode o QR)")

    if st.button("Guardar producto"):
        cursor.execute(
            "INSERT INTO productos (nombre, precio, stock, codigo) VALUES (?,?,?,?)",
            (nombre, precio, stock, codigo)
        )
        conn.commit()
        st.success("Producto agregado")

    st.subheader("Productos")
    cursor.execute("SELECT * FROM productos")
    for p in cursor.fetchall():
        st.markdown(f'<div class="card">{p[1]} - ${p[2]} | Stock: {p[3]}</div>', unsafe_allow_html=True)

# --- ESCÁNER PRO ---
elif menu == "Escaneo PRO":
    st.header("📷 Escaneo en tiempo real")

    if not scanner_ok:
        st.error("⚠️ Escáner no disponible")
        st.info("Instala esto en la terminal:")
        st.code("sudo apt install libzbar0 && pip install streamlit-webrtc pyzbar av")
    else:
        class Scanner(VideoProcessorBase):
            def recv(self, frame):
                img = frame.to_ndarray(format="bgr24")
                codes = decode(img)

                for code in codes:
                    codigo = code.data.decode("utf-8")

                    cursor.execute("SELECT * FROM productos WHERE codigo=?", (codigo,))
                    producto = cursor.fetchone()

                    if producto:
                        if producto not in st.session_state.carrito:
                            st.session_state.carrito.append(producto)

                return av.VideoFrame.from_ndarray(img, format="bgr24")

        webrtc_streamer(
            key="scanner",
            video_processor_factory=Scanner,
            media_stream_constraints={"video": True, "audio": False},
        )

        st.subheader("🛒 Carrito en vivo")
        total = 0

        for item in st.session_state.carrito:
            st.markdown(f'<div class="card">{item[1]} - ${item[2]}</div>', unsafe_allow_html=True)
            total += item[2]

        st.subheader(f"Total: ${total}")

# --- VENTAS ---
elif menu == "Ventas":
    st.header("💰 Finalizar venta")

    total = 0
    for item in st.session_state.carrito:
        st.markdown(f'<div class="card">{item[1]} - ${item[2]}</div>', unsafe_allow_html=True)
        total += item[2]

    st.subheader(f"Total: ${total}")

    if st.button("Finalizar venta"):
        if total > 0:
            fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute("INSERT INTO ventas (fecha, total) VALUES (?,?)", (fecha, total))

            for item in st.session_state.carrito:
                cursor.execute("UPDATE productos SET stock = stock - 1 WHERE id=?", (item[0],))

            conn.commit()
            st.session_state.carrito = []
            st.success("Venta registrada ✅")