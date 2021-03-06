# -*- coding: utf-8 -*-
"""
/***************************************************************************
 GugikNmtDockWidget
                                 A QGIS plugin
 opis
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2019-10-28
        git sha              : $Format:%H$
        copyright            : (C) 2019 by Jakub Skowroński SKNG UAM
        email                : skowronski.jakub97@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os, csv
import urllib.request
from matplotlib import pyplot as plt

from qgis.PyQt import QtGui, uic
from qgis.PyQt.QtWidgets import QDockWidget, QInputDialog, QFileDialog
from qgis.PyQt.QtCore import pyqtSignal, QVariant
from qgis.PyQt.QtGui import QIcon
from qgis.core import (QgsMapLayerProxyModel, QgsField, Qgis, QgsTask, QgsApplication,
    QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProject, QgsVectorLayer, 
    QgsFeature, QgsWkbTypes)
from qgis.utils import iface

from ..tools import IdentifyTool, ProfileTool
from .info_dialog import InfoDialog

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'gugik_nmt_plugin_dockwidget_base.ui'))


class GugikNmtDockWidget(QDockWidget, FORM_CLASS):

    closingPlugin = pyqtSignal()
    on_message = pyqtSignal(str, object, int)

    def __init__(self, parent=None):
        """Constructor."""
        super(GugikNmtDockWidget, self).__init__(parent)
        self.setupUi(self)

        self.registerTools()
        self.setButtonIcons()
        self.on_message.connect(self.showMessage)

        self.savedFeats = []
        self.infoDialog = InfoDialog()

        self.cbLayers.setFilters(QgsMapLayerProxyModel.PointLayer)
        self.cbLayers.layerChanged.connect(self.cbLayerChanged)
        self.tbExtendLayer.clicked.connect(self.extendLayerByHeight)
        self.cbxUpdateField.stateChanged.connect(self.switchFieldsCb)
        self.tbCreateTempLyr.clicked.connect(self.createTempLayer)
        self.tbExportCsv.clicked.connect(self.exportToCsv)
        self.tbShowProfile.clicked.connect(self.generatePlot)
        self.tbInfos.clicked.connect(self.showInfo)
        self.tbResetPoints.clicked.connect(lambda: self.identifyTool.reset())

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()
        
    def showInfo(self):
        self.infoDialog.show()

    def extendLayerByHeight(self):
        """ Rozszerzenie warstwy o pole z wysokością """
        layer = self.cbLayers.currentLayer()
        if not layer:
            return
        if self.cbxUpdateField.isChecked():
            field_id = layer.dataProvider().fields().indexFromName(self.cbFields.currentText())
        elif 'nmt_wys' not in layer.fields().names():
            field_id = self.createNewField(layer)
        else:
            field_id = layer.dataProvider().fields().indexFromName('nmt_wys')
        if self.cbxSelectedOnly.isChecked():
            features = layer.selectedFeatures()
        else:
            features = [f for f in layer.getFeatures()]
        data = {'features':features, 'field_id':field_id}
        self.task2 = QgsTask.fromFunction('Dodawanie pola z wysokościa...', self.addHeightToFields, data=data)
        QgsApplication.taskManager().addTask(self.task2)

    def addHeightToFields(self, task: QgsTask, data):
        #Iteracja po obiektach i dodanie wartości do pola nmt
        features = data.get('features')
        if not features:
            return
        layer = self.cbLayers.currentLayer()
        field_id = data.get('field_id')
        total = 100/len(features)
        for idx, f in enumerate(features):
            fid = f.id()
            geometry = f.geometry()
            height = self.getHeight(geometry, layer=layer)
            field = layer.dataProvider().fields().field(field_id)
            if field.type() in [QVariant.LongLong, QVariant.Int]:
                height = int(float(height))
            layer.dataProvider().changeAttributeValues({fid:{field_id:height}})
            try:
                self.task.setProgress( idx*total )
            except AttributeError as e:
                pass
        self.on_message.emit(f'Pomyślnie dodano pole z wysokościa do warstwy: {layer.name()}', Qgis.Success, 4)
        del self.task2

    def createNewField(self, layer):
        """ Utworzenie nowego pola i znalezienie id """
        #Dodanie nowego pola o podanych parametrach
        data_provider = layer.dataProvider()
        data_provider.addAttributes([QgsField('nmt_wys', QVariant.Double)])
        layer.reload()
        #Znalezienie id pola
        field_id = data_provider.fields().indexFromName('nmt_wys')
        return field_id

    def getHeight(self, geom, layer=None, special=False):
        """ Wysłanie zapytania do serwisu GUGiK NMT po wysokość w podanych współrzędnych """
        # http://services.gugik.gov.pl/nmt/?request=GetHbyXY&x=486617&y=637928
        point = geom.asPoint()
        if special:
            x, y = point.y(), point.x()
            try:
                r = urllib.request.urlopen(f'https://services.gugik.gov.pl/nmt/?request=GetHbyXY&x={x}&y={y}')
                return r.read().decode()
            except Exception as e:
                self.on_message.emit(str(e), Qgis.Critical, 5)
                return
        
        if layer:
            if layer.crs().authid() != 'EPSG:2180':
                point = self.coordsTransform(point, 'EPSG:2180', layer=layer)
        else:
            if QgsProject.instance().crs().authid() != 'EPSG:2180':
                point = self.coordsTransform(point, 'EPSG:2180')
        x, y = point.y(), point.x()
        try:
            # f'http://services.gugik.gov.pl/nmt/?request=GetHbyXY&x={x}&y={y} 22'
            r = urllib.request.urlopen(f'https://services.gugik.gov.pl/nmt/?request=GetHbyXY&x={x}&y={y}')
            return r.read().decode()
        except Exception as e:
            self.on_message.emit(str(e), Qgis.Critical, 5)
            return

    def switchFieldsCb(self, state):
        """ Aktualizowanie combo boxa z polami """
        self.cbFields.setEnabled(state)
        self.cbFields.clear()
        layer = self.cbLayers.currentLayer()
        if not layer:
            return
        if not state:
            return
        self.cbFields.addItems([fname for fname in layer.fields().names()])

    def registerTools(self):
        self.identifyTool = IdentifyTool(self)
        self.identifyTool.setButton(self.tbGetPoint)
        self.tbGetPoint.clicked.connect(lambda: self.activateTool(self.identifyTool))
        
        self.profileTool = ProfileTool(self)
        self.profileTool.setButton(self.tbMakeLine)
        self.tbMakeLine.clicked.connect(lambda: self.activateTool(self.profileTool))

    def activateTool(self, tool):
        iface.mapCanvas().setMapTool(tool)
        if tool == self.profileTool:
            self.dsbLineLength.setEnabled(True)

    def coordsTransform(self, geom, epsg, layer=None):
        if layer:
            activeCrs = layer.crs().authid()
        else:
            activeCrs = QgsProject.instance().crs().authid()
        fromCrs = QgsCoordinateReferenceSystem(activeCrs)
        toCrs = QgsCoordinateReferenceSystem(epsg)
        transformation = QgsCoordinateTransform(fromCrs, toCrs, QgsProject.instance())
        geom = transformation.transform(geom)
        return geom

    def createTempLayer(self):
        if not self.savedFeats:
            self.on_message.emit('Brak punktów do zapisu', Qgis.Warning, 5)
            return
        text, ok = QInputDialog.getText(self, 'Stwórz warstwę tymczasową', 'Nazwa warstwy:')
        if not ok:
            return
        epsg = QgsProject.instance().crs().authid()
        self.tempLayer = QgsVectorLayer(f'Point?crs={epsg.lower()}&field=id:integer&field=nmt_wys:double', text, 'memory')
        QgsProject.instance().addMapLayer(self.tempLayer)
        self.task = QgsTask.fromFunction('Dodawanie obiektów', self.populateLayer, data=self.savedFeats)
        QgsApplication.taskManager().addTask(self.task)

    def populateLayer(self, task: QgsTask, data):
        lyr_fields = self.tempLayer.fields()
        total = 100/len(data)
        features = []
        for idx, tempFeat in enumerate(data):
            f = QgsFeature(lyr_fields)
            f.setGeometry(tempFeat.get('geometry'))
            attributes = [idx, tempFeat.get('height')]
            f.setAttributes(attributes)
            features.append(f)
            try:
                self.task.setProgress( idx*total )
            except AttributeError:
                pass
        self.tempLayer.dataProvider().addFeatures(features)
        self.tempLayer.updateExtents(True)
        self.on_message.emit(f'Utworzono warstwę tymczasową: {self.tempLayer.name()}', Qgis.Success, 4)
        self.identifyTool.reset()
        del self.task

    def exportToCsv(self):
        rows = self.twData.rowCount()
        if rows < 1:
            return
        path, _ = QFileDialog.getSaveFileName(filter=f'*.csv')
        if not path:
            return   
        rows = self.twData.rowCount()
        if not path.lower().endswith('.csv'):
            path += '.csv'
        with open(path, 'w') as f:
            writer = csv.writer(f, delimiter=';')
            to_write = [['Odległość', 'Wysokość npm']]
            for row in range(rows):
                dist = self.twData.item(row, 0).text().replace('.', ',') + 'm'
                val = self.twData.item(row, 1).text().replace('.', ',')
                to_write.append([dist, val])
            writer.writerows(to_write)
        self.on_message.emit(f'Wygenerowano plik csv w miejscu: {path}', Qgis.Success, 4)   

    def generatePlot(self):
        rows = self.twData.rowCount()
        if rows < 1:
            return
        dist_list = []
        values = []
        for row in range(rows):
            dist = self.twData.item(row, 0).text()
            val = self.twData.item(row, 1).text()
            dist_list.append(float(dist))
            values.append(float(val))
        
        fig, ax = plt.subplots()
        ax.set(xlabel='Interwał [m]', ylabel='Wysokość npm',
            title='Profil podłużny')
        ax.plot(dist_list, values)
        plt.show()

    def cbLayerChanged(self):
        self.cbxUpdateField.setChecked(False)
        self.cbFields.clear()

    def setButtonIcons(self):
        self.tbGetPoint.setIcon(QIcon(':/plugins/gugik_nmt_plugin/icons/index.svg'))
        self.tbExportCsv.setIcon(QgsApplication.getThemeIcon('mActionAddTable.svg'))
        self.tbCreateTempLyr.setIcon(QgsApplication.getThemeIcon('mActionFileSave.svg'))
        self.tbExtendLayer.setIcon(QgsApplication.getThemeIcon('mActionStart.svg'))
        self.tbMakeLine.setIcon(QgsApplication.getThemeIcon('mActionAddPolyline.svg'))
        self.tbShowProfile.setIcon(QgsApplication.getThemeIcon('mActionAddImage.svg'))
        self.tbResetPoints.setIcon(QgsApplication.getThemeIcon('mIconDelete.svg'))

    def showMessage(self, message, level, time=5):
        iface.messageBar().pushMessage('Wtyczka GUGiK NMT:', message, level, time)