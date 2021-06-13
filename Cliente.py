import sqlite3
import cloudinary
import Funciones_cliente as f
import shutil

miConexion = sqlite3.connect("Data")
miCursor = miConexion.cursor()

cloudinary.config( #Añade aqui los datos de tu cuenta de Cloudinary
    cloud_name=,
    api_key=,
    api_secret=
)

carpetas = f.obtener_carpeta(miCursor)[0] #Correcta
f.descarga_imagenes(carpetas,miCursor,miConexion) #Correcta


res = f.Keras_Retinanet(carpetas,miCursor,miConexion) #Correcta
if res:
    mejores_fotos = f.Encontrar_mejores(carpetas,miCursor)
    f.Keras_ocr(carpetas,mejores_fotos,miCursor,miConexion)
else:
    shutil.rmtree('/' + str(carpetas))


f.consulta_resultados(miCursor)
