import cloudinary
import cloudinary.api
from os import mkdir
import shutil
import requests
import os
from keras_retinanet import models as retinamodels
from keras_retinanet.utils.image import read_image_bgr, preprocess_image, resize_image
from keras_retinanet.utils.visualization import draw_box, draw_caption
from keras_retinanet.utils.colors import label_color
import numpy as np
import cv2
import math
import matplotlib.pyplot as plt
from os import listdir
from os.path import isfile, join
from skimage import io
import keras_ocr


def string2list (str):  #'[array([ 559,  199, 1049,  440]), array([ 15, 209, 667, 420])]'
  cachos = str.split('array(')
  res = []
  i = 1
  while i < len(cachos):
    a = cachos[i].split(',')
    j = 0
    parcial = []
    while j < 4:
      if j == 0:
        a[j] = a[j].strip('[')
        parcial.append(int(a[j]))
      elif j == 3:
        a[j] = a[j].strip('])')
        parcial.append(int(a[j]))
      else:
        parcial.append(int(a[j]))
      j += 1
    res.append(parcial)
    i += 1
  return res

def distinguir(vector):
  ancho = abs(vector[1][0] - vector[0][0])
  alto = abs(vector[0][1] - vector[3][1])
  return (ancho/alto)

def palabras_clave(texto,palabras):
  for word in palabras:
    if word.lower() == texto.lower() or texto.lower() in word.lower() or word.lower() in texto.lower():
      return True
  return False

def mucho_angulo(box):
  hlado = math.sqrt(((box[0][0]-box[3][0])**2) + ((box[0][1]-box[3][1])**2))
  hrot = abs(box[3][1]-box[2][1])
  if hlado*1.5 < hrot:
    return True
  else:
    return False

def relacionaspecto(box):
  ancho = math.sqrt((box[1][0] - box[0][0])**2 + (box[1][1] - box[0][1])**2)
  alto = math.sqrt((box[0][1] - box[3][1])**2 + (box[0][0] - box[3][0])**2)
  ar = (ancho/alto)
  if ar < 7.75:
    return False
  else:
    return True

def filtro_dimensiones(vector,numero,avion):
  coordx = []; coordy = []; ordenado = [0,0,0,0];
  for punto in vector:
    coordx.append(round(punto[0],2)); coordy.append(round(punto[1],2))

  max_x = max(coordx); max_y = max(coordy)
  min_x = min(coordx); min_y = min(coordy)
  indiceax = [i for i, j in enumerate(coordx) if j == max_x]; indiceay = [i for i, j in enumerate(coordy) if j == max_y]
  indiceix = [i for i, j in enumerate(coordx) if j == min_x]; indiceiy = [i for i, j in enumerate(coordy) if j == min_y]
  if len(indiceax + indiceay + indiceix + indiceiy) > 4:  # Rectangulo sin girar
    ordenado[0] = vector[list(set(indiceix).intersection(indiceiy))[0]]
    ordenado[2] = vector[list(set(indiceax).intersection(indiceay))[0]]
    ordenado[1] = vector[list(set(indiceiy).intersection(indiceax))[0]]
    ordenado[3] = vector[list(set(indiceay).intersection(indiceix))[0]]
  else:  # Rectangulo girado
    indiceax = indiceax[0]; indiceay = indiceay[0]; indiceix = indiceix[0]; indiceiy = indiceiy[0];
    t2 = [vector[indiceix],vector[indiceiy],vector[indiceax],vector[indiceay]]
    t3 = [vector[indiceiy],vector[indiceax],vector[indiceay],vector[indiceix]]
    if  distinguir(t2) > 1.0:
      ordenado = t2
    else:
      ordenado =t3
  if mucho_angulo(ordenado):
    return True
  elif relacionaspecto(ordenado):
    return True
  elif comprobar(ordenado,numero,avion):
    return True
  else:
    return False

def filtro_contenido(palabra, conjuntos):
  if 8 <= len(palabra):
    return True
  elif 3 >= len(palabra):
    return True
  elif 'oooo' in palabra:
    return True
  elif palabras_clave(palabra, conjuntos):
    return True
  else:
    return False

def calcular_centro(box):
  centro_x = (box[0][0] + box[2][0])/2
  centro_y = (box[0][1] + box[2][1])/2
  return [centro_x,centro_y]

def centro_dentro(avion,centro):
  if avion[0] <= centro[0] <= avion[2] and avion[1] <= centro[1] <= avion[3]:
    return False
  else:
    return True

def comprobar (box,numero,avion):
  if numero == 1:
    centro = calcular_centro(box)
    resultado = centro_dentro(avion,centro)
    return resultado
  else:
    resultados =[]
    i = 0
    while i < len(avion):
      centro = calcular_centro(box)
      resultado = centro_dentro(avion[i], centro)
      resultados.append(resultado)
      i += 1
    if False in resultados:
      return False
    else:
      return True

def obtener_aviones (foto,miCursor,carpeta):
    querylocalizacionaviones = "SELECT Numero_aviones,Localizacion FROM FOTOS WHERE Nombre_carpeta= '" + str(carpeta) + "' AND Nombre_foto= '" + str(foto)+"'"
    miCursor.execute(querylocalizacionaviones)
    localizaciones = miCursor.fetchall()
    numero = localizaciones[0][0]
    avion = string2list(localizaciones[0][1])[0]
    return (numero,avion)

def textos (grupos,palabras,miCursor,imagenes,carpeta):
  grp = len(grupos) #numero de fotos
  i = 0
  indexes = []
  while i < grp:
    box = len(grupos[i]) #numero de cajas en la foto
    nume, avio = obtener_aviones(imagenes[i],miCursor,carpeta)
    n = 0
    while n < box:
      if filtro_contenido(grupos[i][n][0],palabras) or filtro_dimensiones(grupos[i][n][1],nume,avio):
        indexes.append(n)
      n+=1
    for index in sorted(indexes, reverse=True):
      del grupos[i][index]
    indexes = []
    i+=1

def solo_string(grupos):
  strings = [[],[],[]]
  n = 0
  for foto in grupos:
    for box in foto:
      strings[n].append(box[0])
    n += 1
  return strings

def distanciasimple(string1, string2, distancia):
    n = 0;
    r = 0
    s1rev = string1[::-1]
    s2rev = string2[::-1]
    drev = 0
    errores_comunes = ['0o', 'o0', 'a4', '4a', 'z7', '7z', 'il', 'li', 'g9', '9g', '5s', 's5', 'i1', '1i', '8b', 'b8']
    while n < len(string1):
        if string1[n] != string2[n]:
            erroneas = string1[n] + string2[n]
            if '-' in erroneas or (erroneas in errores_comunes):
                distancia = distancia
            else:
                if n == 0 or n == len(string1) - 1:
                    distancia += 1.1
                else:
                    distancia += 1
        n += 1

    while r < len(s1rev):
        if s1rev[r] != s2rev[r]:
            erroneas = s1rev[r] + s2rev[r]
            if '-' in erroneas or (erroneas in errores_comunes):
                drev = drev
            else:
                if r == 0 or r == len(s1rev) - 1:
                    drev += 1.1
                else:
                    drev += 1
                drev += 1
        r += 1
    if drev < distancia:
        distancia = drev

    return distancia

def coincidencia(string1, string2):
    s1rev = string1[::-1]
    s2rev = string2[::-1]
    m = len(string1) - 1
    if (string1[:2] == string2[:2] and s1rev[:2] == s2rev[:2]) or string1[:4] == string2[:4] or s1rev[:4] == s2rev[:4]:
        return 1.75
    elif string1[:m] == string2[:m] or s1rev[:m] == s2rev[:m]:
        return 1.75
    else:
        return 10

def arbol_distancias(string1, string2):  # string1 prediccion string2 respuesta
    string1 = string1.lower();
    string2 = string2.lower();
    parcial = string2.replace('-', '')
    distancia = 0
    if string1 == string2:
        return -1
    elif string1 == parcial:
        return -1
    elif len(string1) == len(string2):
        return distanciasimple(string1, string2, distancia) - 0.5
    elif len(string1) + 1 == len(string2):
        if '-' in string2:
            string2 = string2.replace('-', '')
            return distanciasimple(string1, string2, distancia)
        elif string1 in string2:
            return 1
        else:
            string2i = string2[1:]
            string2f = string2[:-1]
            d1 = distanciasimple(string1, string2i, distancia)
            d2 = distanciasimple(string1, string2f, distancia)
            if d1 < d2:
                distancia = d1
            else:
                distancia = d2
            return distancia
    elif string1 in string2:
        return 1
    else:
        distancia = coincidencia(string1, parcial)
    return distancia

def distancia_mia(predicciones, lista_matriculas):
    matriculas_candidatas = []
    for pred in predicciones:
        distancias = []
        for matricula in lista_matriculas:
            distancias.append(arbol_distancias(pred, matricula))
        indexmin = distancias.index(min(distancias))
        matriculas_candidatas.append(lista_matriculas[indexmin])

    d = 10
    matricula_encontrada = ''

    for pred in predicciones:
        for candidato in matriculas_candidatas:
            dnueva = arbol_distancias(pred, candidato)
            if dnueva < d:
                d = dnueva
                matricula_encontrada = candidato
    return matricula_encontrada,d

def ordenar(e):
    return e[0]

def obtener_carpeta(miCursor):
    #Obtener las carpetas procesadas
    query_carpetas = "SELECT DISTINCT Nombre_carpeta from FOTOS"
    miCursor.execute(query_carpetas)
    carpetasBBDD = miCursor.fetchall()

    #Obtener carpetas en la web
    vector_carpetas = cloudinary.api.root_folders()
    carpetas = []
    for carpeta in vector_carpetas['folders']:
        carpetas.append(carpeta['name'])

    #Obtener matriculas no procesadas
    diferencia = list(set(carpetas) - set(carpetasBBDD))

    return diferencia

def descarga_imagenes(carpeta,miCursor,miConexion):
    newpath = r'./' + str(carpeta)
    mkdir(newpath)
    os.chdir(newpath)

    res = cloudinary.Search() \
        .expression('folder:' + str(carpeta) + '/*') \
        .execute()

    for foto in res['resources']:
        nombre_foto = foto['public_id'].split('/')[1]
        direccion_foto = cloudinary.utils.cloudinary_url(str(carpeta) + '/' + str(nombre_foto) + ".jpg",resource_type="image")
        response = requests.get(direccion_foto[0])
        file = open(str(nombre_foto) + ".jpg", "wb")
        file.write(response.content)
        file.close()
        valores = (str(carpeta),str(nombre_foto),'null',0,'null','null')
        query_aniadir = "INSERT INTO FOTOS (Nombre_carpeta,Nombre_foto,Rel_areas,Numero_aviones,Localizacion,Matricula) VALUES " + str(valores)
        miCursor.execute(query_aniadir)
        miConexion.commit()

def Keras_Retinanet (carpeta,miCursor,miConexion):
    model_path = os.path.join('C:/Users/marti/Desktop/Cliente/keras_retinanet', 'resnet50_coco_best_v2.1.0.h5')
    model = retinamodels.load_model(model_path, backbone_name='resnet50')
    labels_to_names = {0: 'person', 1: 'bicycle', 2: 'car', 3: 'motorcycle', 4: 'airplane', 5: 'bus', 6: 'train',
                       7: 'truck',
                       8: 'boat', 9: 'traffic light', 10: 'fire hydrant', 11: 'stop sign', 12: 'parking meter',
                       13: 'bench',
                       14: 'bird', 15: 'cat', 16: 'dog', 17: 'horse', 18: 'sheep', 19: 'cow', 20: 'elephant',
                       21: 'bear',
                       22: 'zebra', 23: 'giraffe', 24: 'backpack', 25: 'umbrella', 26: 'handbag', 27: 'tie',
                       28: 'suitcase',
                       29: 'frisbee', 30: 'skis', 31: 'snowboard', 32: 'sports ball', 33: 'kite', 34: 'baseball bat',
                       35: 'baseball glove', 36: 'skateboard', 37: 'surfboard', 38: 'tennis racket', 39: 'bottle',
                       40: 'wine glass', 41: 'cup', 42: 'fork', 43: 'knife', 44: 'spoon', 45: 'bowl', 46: 'banana',
                       47: 'apple', 48: 'sandwich', 49: 'orange', 50: 'broccoli', 51: 'carrot', 52: 'hot dog',
                       53: 'pizza',
                       54: 'donut', 55: 'cake', 56: 'chair', 57: 'couch', 58: 'potted plant', 59: 'bed',
                       60: 'dining table',
                       61: 'toilet', 62: 'tv', 63: 'laptop', 64: 'mouse', 65: 'remote', 66: 'keyboard',
                       67: 'cell phone',
                       68: 'microwave', 69: 'oven', 70: 'toaster', 71: 'sink', 72: 'refrigerator', 73: 'book',
                       74: 'clock',
                       75: 'vase', 76: 'scissors', 77: 'teddy bear', 78: 'hair drier', 79: 'toothbrush'}

    directorio = "C:/Users/marti/Desktop/Cliente/" + str(carpeta)
    imagenes = [r for r in listdir(directorio) if isfile(join(directorio, r))]
    avionesdetectados = 0

    for foto in imagenes:
        image = read_image_bgr(directorio+'/' + foto)
        nombre_foto = foto.split('.')[0]
        draw = image.copy()
        draw = cv2.cvtColor(draw, cv2.COLOR_BGR2RGB)
        image = preprocess_image(image)
        image, scale = resize_image(image)
        boxes, scores, labels = model.predict_on_batch(np.expand_dims(image, axis=0))
        boxes /= scale
        aviones = []

        for box, score, label in zip(boxes[0], scores[0], labels[0]):
            # scores are sorted so we can break
            if score < 0.5:
                break

            color = label_color(label)

            b = box.astype(int)
            draw_box(draw, b, color=color)

            caption = "{} {:.3f}".format(labels_to_names[label], score)
            draw_caption(draw, b, caption)
            if 'airplane' in caption:
                aviones.append(b)

        if aviones != []:
            ratios = ''
            for avion in aviones:
                fotoarea = io.imread(directorio+'/' + foto)
                dimensiones = fotoarea.shape
                areaImagen = dimensiones[0] * dimensiones[1] #Alto*Ancho
                areaAvion = (avion[2]-avion[0]) * (avion[3]-avion[1])
                ratio = areaAvion/areaImagen
                ratios += str(round(ratio,2)) + '/'

            queryaviones = "UPDATE FOTOS SET Rel_areas= '"+str(ratios)+"', Numero_aviones= '"+str(len(aviones))+"', Localizacion= '"+str(aviones)+"' WHERE Nombre_foto = '"+ str(nombre_foto)+"'"
            miCursor.execute(queryaviones)
            miConexion.commit()
            avionesdetectados += 1
    if avionesdetectados != 0:
        return True
    else:
        return False

def Encontrar_mejores(carpeta,miCursor):
    query_mejores = "SELECT Nombre_foto,Numero_aviones,Rel_areas FROM FOTOS WHERE Nombre_carpeta= '" + str(carpeta)+"'"
    miCursor.execute(query_mejores)
    set_datos = miCursor.fetchall()


    nomrel = [[0,set_datos[0][0]]]#Añade un elemento que no ganara para poder hacer .extend()

    for foto in set_datos:
        if int(foto[1]) != 0:
            if int(foto[1]) == 1:
                nomrel.append([float(foto[2].split('/')[0]),foto[0]])
            elif int(foto[1]) > 1:
                n = 0
                while n < foto[1]:
                    nomrel.append([float(foto[2].split('/')[n]),foto[0]])
                    n+=1
        else:
            continue


    nomrel.sort(key=ordenar,reverse=True)

    imagenes = (nomrel[0][1],nomrel[1][1],nomrel[2][1]) #Mejores fotos

    return imagenes

def Keras_ocr (carpeta,imagenes,miCursor,miConexion):
    pipeline = keras_ocr.pipeline.Pipeline()
    palabras = []
    matriculas = []
    with open('C:/Users/marti/Desktop/Cliente/Aerolineas.txt') as my_file:
        for line in my_file:
            line = line.rstrip('\n')
            palabras.append(line)

    with open('C:/Users/marti/Desktop/Cliente/matriculas.txt') as my_file:
        for line in my_file:
            line = line.rstrip('\n')
            matriculas.append(line)

    images = []
    for imagen in imagenes:
        img = io.imread('C:/Users/marti/Desktop/Cliente/' + carpeta + '/' + imagen+'.jpg')
        images.append(img)

    prediction_groups = pipeline.recognize(images)

    textos(prediction_groups,palabras,miCursor,imagenes,carpeta)
    strings = solo_string(prediction_groups)
    encontradas = []
    for i in range(len(strings)):
        matricula,distancia = (distancia_mia(strings[i],matriculas))
        encontradas.append([distancia,matricula,imagenes[i]])

    for i in range (3):
        queryguardarmejores = "UPDATE FOTOS SET Matricula= '"+str(encontradas[i][1])+"' WHERE Nombre_foto= '"+str(imagenes[i])+"' AND Nombre_carpeta= '"+str(carpeta)+ "'"
        miCursor.execute(queryguardarmejores)
        miConexion.commit()

    encontradas.sort(key=ordenar)
    img = io.imread('C:/Users/marti/Desktop/Cliente/'+ carpeta + '/' + str(encontradas[0][2])+'.jpg')
    plt.imshow(img)
    plt.savefig('C:/Users/marti/Desktop/Cliente/Matriculas_encontradas/' + str(encontradas[0][1])+'.jpg')

    queryencontrada = "INSERT INTO ENCONTRADAS (foto,matricula)VALUES "+str((str(encontradas[0][2]),str(encontradas[0][1])))
    miCursor.execute(queryencontrada)
    miConexion.commit()

    shutil.rmtree('C:/Users/marti/Desktop/Cliente/'+str(carpeta))

def consulta_resultados(miCursor):
    queryresultados = "SELECT * FROM ENCONTRADAS"
    miCursor.execute(queryresultados)
    datos = miCursor.fetchall()

    for elemento in datos:
        letras = list(elemento[0].split('-')[0]) #20210501-20_59_01_augna3
        fecha = letras[0]+letras[1]+letras[2]+letras[3]+'/'+letras[4]+letras[5]+'/'+letras[6]+letras[7]
        letras1 = letras[1].split('_')
        hora = letras1[0]+':'+letras1[1]+':'+letras1[2]
        print("El "+str(fecha)+" a las "+str(hora)+" se encontró la matricula "+str(elemento[1]+" la prueba es la foto "+str(elemento[0]+" de la carpeta Matriculas_encontradas")))

