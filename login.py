# login.py
import streamlit as st

# 1. LISTA DE ESTUDIANTES Y PROFESORES AUTORIZADOS
# Puedes agregar, cambiar o borrar correos y claves aquí fácilmente cada semestre:
ESTUDIANTES_VALIDOS = {
    "alumno1@correo.com": "clave123",
    "alumno2@correo.com": "estudiante2026",
    "camilo@camilojimenez.com": "screener2026",
    "admin@camilojimenez.com": "admin123"
}

def requerir_autenticacion() -> bool:
    """
    Verifica si el usuario ha iniciado sesión. 
    Si no lo ha hecho, muestra la pantalla de ingreso y bloquea el resto de la app.
    """
    # Inicializar la variable de control de sesión en la memoria temporal
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False

    # Si ya ingresó correctamente antes, le damos paso inmediato
    if st.session_state["autenticado"]:
        return True

    # -------------------------------------------------------------
    # DISEÑO DEL FORMULARIO DE INGRESO
    # -------------------------------------------------------------
    st.markdown("<br><br>", unsafe_allow_html=True) # Espaciado superior
    st.markdown("<h2 style='text-align: center; font-family: Syne, sans-serif;'>📊 Portal de Inversiones - Camilo Jiménez</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #888888;'>Por favor, ingresa con tu correo y clave predeterminada para acceder al Stock Screener</p>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    with st.container():
        # Columnas para que el formulario quede perfectamente centrado en la pantalla
        col_vacia1, col_formulario, col_vacia2 = st.columns([1, 2, 1])
        
        with col_formulario:
            correo = st.text_input("Correo Electrónico:", placeholder="ejemplo@correo.com")
            clave = st.text_input("Contraseña:", type="password")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("Ingresar a la Plataforma 🚀", use_container_width=True):
                # Limpiamos espacios en blanco por si el alumno pegó su correo con un espacio al final
                correo_limpio = correo.strip().lower()
                
                if correo_limpio in ESTUDIANTES_VALIDOS and ESTUDIANTES_VALIDOS[correo_limpio] == clave:
                    st.session_state["autenticado"] = True
                    st.success("¡Acceso concedido! Cargando herramientas de análisis...")
                    st.rerun() # Recarga instantánea para mostrar el screener
                else:
                    st.error("⚠️ El correo o la contraseña no coinciden. Por favor verifica tus datos.")

    # Si el usuario aún no ha iniciado sesión, retornamos False
    return False


def boton_cerrar_sesion():
    """
    Muestra un botón en la barra lateral (sidebar) para poder salir de la cuenta.
    """
    with st.sidebar:
        st.markdown("---")
        if st.button("🔒 Cerrar Sesión", use_container_width=True):
            st.session_state["autenticado"] = False
            st.rerun()
