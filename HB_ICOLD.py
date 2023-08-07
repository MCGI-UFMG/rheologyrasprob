import win32com.client
import pandas as pd
import re as re
import numpy as np
import h5py
from osgeo import ogr
from osgeo import osr

RC = win32com.client.Dispatch("RAS610.HECRASCONTROLLER")
parametros = pd.read_csv('C:\\Users\\Malena\\PycharmProjects\\cv1\\param_final_bingham.txt', sep=" ")

# ADEQUAR CÓDIGO

# Variação dos parâmetros
for index, linha in parametros.iterrows():
    sim = index + 1
    cv = linha['Cv']
    cvmax = linha['Cvmax']
    a = linha['a']
    b = linha['b']

    # Lendo as linhas do arquivo unsteady
    with open('D:\Malena\Academico\RAS\ZENZ_GOLDGRUBER\zenz_goldgruber.u01', 'r') as f:
        dados = f.readlines()

        # Encontrando a linha do parâmetro de interesse e definindo a linha como sendo o antigo parâmetro
        for line in dados:
            if re.search(r'Non-Newtonian Constant Vol Conc', line):
                break
        antp_cv = line

        for line in dados:
            if re.search(r'Non-Newtonian Max Cv', line):
                break
        antp_cvmax = line

        for line in dados:
            if re.search(r'Non-Newtonian Yield Coef', line):
                break
        antp_a_b = line

    # Abrindo e salvando arquivo para alterar a linha do parâmetro anterior pelo novo valor
    with open('D:\Malena\Academico\RAS\ZENZ_GOLDGRUBER\zenz_goldgruber.u01', 'r') as f:
        dados = f.read()
    novop_cv = 'Non-Newtonian Constant Vol Conc=' + str(cv) + '\n'
    novop_cvmax = 'Non-Newtonian Max Cv=' + str(cvmax) + '\n'
    novop_a_b = 'Non-Newtonian Yield Coef=' + str(a) + ', ' + str(b) + '\n'

    print('Simulação %d - ' % sim, novop_cv, novop_cvmax, novop_a_b)
    dados = dados.replace(antp_cv, novop_cv)
    dados = dados.replace(antp_cvmax, novop_cvmax)
    dados = dados.replace(antp_a_b, novop_a_b)

    with open('D:\Malena\Academico\RAS\ZENZ_GOLDGRUBER\zenz_goldgruber.u01', 'w') as f:
        f.write(dados)

    # Abrindo o projeto no RAS e simulando com parâmetros alterados
    RC.ShowRAS()
    RC.Project_Open(r"D:\Malena\Academico\RAS\ZENZ_GOLDGRUBER\zenz_goldgruber.prj")
    RC.Compute_CurrentPlan(None, None, True)
    RC.QuitRAS()

    # Salvando resultados de profundidades máximas em cada célula
    file = "D:\\Malena\\Academico\\RAS\\ZENZ_GOLDGRUBER\\zenz_goldgruber.p01.hdf"
    with h5py.File(file, "r") as hdf:
        celldepth = hdf.get(
            '/Results/Unsteady/Output/Output Blocks/Base Output/Unsteady Time Series/2D Flow Areas/jusante/Cell Hydraulic Depth')
        depthmax = np.amax(celldepth, axis=0)
        depthmax_delsa = h5py.File('depth_max_delsa.hdf', 'a')
        depthmax_delsa.create_dataset('sim_%d' % sim, data=depthmax)
        depthmax_delsa.close()

    # Acessando e salvando as velocidades máximas em cada célula por simulação realizada
    with h5py.File(file, "r") as hdf:
        facevelocity = hdf.get(
            '/Results/Unsteady/Output/Output Blocks/Base Output/Unsteady Time Series/2D Flow Areas/jusante/Face Velocity')
        velmax = np.amax(facevelocity, axis=0)

        velmax_delsa = h5py.File('velocity_max_delsa.hdf', 'a')
        velmax_delsa.create_dataset('sim_%d' % sim, data=velmax)
        velmax_delsa.close()

    # Acessando as profundidades em cada célula e salvando tempos de chegada para 0,61 (2 pés) por simulação realizada
    with h5py.File(file, "r") as hdf:
        celldepth = hdf.get(
            '/Results/Unsteady/Output/Output Blocks/Base Output/Unsteady Time Series/2D Flow Areas/jusante/Cell Hydraulic Depth')
        depth = np.array(celldepth)
        tempos = []
        transp_depth = depth.transpose()

        for y in transp_depth:
            print(y)
            list = y.tolist()
            for x in y:
                if x > 0.61:
                    tempo = list.index(x)
                    tempos.append(tempo)
                    break
                else:
                    tempo = 0
                    tempos.append(tempo)
                    break

        tempo_chegada = h5py.File('tempo_chegada61.hdf', 'a')
        tempo_chegada.create_dataset('sim_%d' % sim, data=tempos)
        tempo_chegada.close()

    # Salvando tempos de chegada para 0,30 (1 pé) por simulação realizada
        for y in transp_depth:
            print(y)
            list = y.tolist()
            for x in y:
                if x > 0.30:
                    tempo = list.index(x)
                    tempos.append(tempo)
                    break
                else:
                    tempo = 0
                    tempos.append(tempo)
                    break

        tempo_chegada = h5py.File('tempo_chegada30.hdf', 'a')
        tempo_chegada.create_dataset('sim_%d' % sim, data=tempos)
        tempo_chegada.close()

    # Acessando e salvando resultados de área da mancha
    driver = ogr.GetDriverByName('ESRI Shapefile')
    hinputfile = driver.Open(r'D:\Malena\Academico\RAS\ZENZ_GOLDGRUBER\plan\Inundation Boundary (Max Value_0).shp', 0)
    in_layer = hinputfile.GetLayer(0)

    # Transformação entre projeções
    src_srs = in_layer.GetSpatialRef()
    tgt_srs = osr.SpatialReference()
    tgt_srs.ImportFromEPSG(3395)
    transform = osr.CoordinateTransformation(src_srs, tgt_srs)

    for feature in in_layer:
        geom = feature.GetGeometryRef()
        geom2 = geom.Clone()
        geom2.Transform(transform)
        area_m2 = geom2.GetArea()
        area_km2 = area_m2 / 1000000
        print('Area em km²: ', area_km2)
        area_delsa = h5py.File('area_delsa.hdf', 'a')
        area_delsa.create_dataset('sim_%d' % sim, data=area_km2)
        area_delsa.close()

    # Armazenando o erro de volume em 1000 m3 e em porcentagem por simulação
    with open('D:\Malena\Academico\RAS\ZENZ_GOLDGRUBER\zenz_goldgruber.p01.computeMsgs.txt', 'r') as f:
        dados = f.readlines()
        erro_vol = []
        erro_volperc = []

        for line in dados:
            if re.search(r'Overall Volume Accounting Error in 1000', line):
                erro_vol.append(line)
                with open('erro_vol.txt', 'a') as txt:
                    txt.write(str(erro_vol))
                break

        for line in dados:
            if re.search(r'Overall Volume Accounting Error as percentage', line):
                erro_volperc.append(line)
                with open('erro_volperc.txt', 'a') as txt:
                    txt.write(str(erro_volperc))
                break

    print('Fim simulação ', sim)
    hinputfile.Destroy()
else:
    print("Simulações com LHS finalizadas.")
