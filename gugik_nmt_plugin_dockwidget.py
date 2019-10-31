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

import os
import urllib.request

from qgis.PyQt import QtGui, uic
from qgis.PyQt.QtWidgets import QDockWidget, QInputDialog, QFileDialog
from qgis.PyQt.QtCore import pyqtSignal, QVariant
from qgis.core import (QgsMapLayerProxyModel, QgsField, Qgis, QgsTask, QgsApplication,
    QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProject, QgsVectorLayer, 
    QgsFeature, QgsWkbTypes)
from qgis.utils import iface

from .tools import IdentifyTool, ProfileTool

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'gugik_nmt_plugin_dockwidget_base.ui'))


class GugikNmtDockWidget(QDockWidget, FORM_CLASS):

    closingPlugin = pyqtSignal()

    def __init__(self, parent=None):
        """Constructor."""
        super(GugikNmtDockWidget, self).__init__(parent)
        self.setupUi(self)

        self.registerTools()

        self.savedFeats = []

        self.cbLayers.setFilters(QgsMapLayerProxyModel.PointLayer)
        self.cbLayers.layerChanged.connect(self.cbLayerChanged)
        self.tbExtendLayer.clicked.connect(self.extendLayerByHeight)
        self.cbxUpdateField.stateChanged.connect(self.switchFieldsCb)
        self.tbCreateTempLyr.clicked.connect(self.createTempLayer)
        self.tbExportCsv.clicked.connect(self.exportToCsv)

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

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
            features = layer.getFeatures()
        #Iteracja po obiektach i dodanie wartości do pola nmt
        for f in features:
            fid = f.id()
            geometry = f.geometry()
            height = self.getHeight(geometry, layer=layer)
            field = layer.dataProvider().fields().field(field_id)
            if field.type() in [QVariant.LongLong, QVariant.Int]:
                height = int(float(height))
            layer.dataProvider().changeAttributeValues({fid:{field_id:height}})

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
            x, y = point.x(), point.y()
            try:
                print(f'http://services.gugik.gov.pl/nmt/?request=GetHbyXY&x={x}&y={y}')
                r = urllib.request.urlopen(f'http://services.gugik.gov.pl/nmt/?request=GetHbyXY&x={x}&y={y}')
                return r.read().decode()
            except Exception as e:
                iface.messageBar().pushMessage('Wtyczka GUGiK NMT:', str(e), Qgis.Critical, 5)
                return
        
        if layer:
            if layer.crs().authid() != 'EPSG:2180':
                point = self.coordsTransform(point, 'EPSG:2180')
        else:
            if QgsProject.instance().crs().authid() != 'EPSG:2180':
                point = self.coordsTransform(point, 'EPSG:2180')
        x, y = point.x(), point.y()
        try:
            f'http://services.gugik.gov.pl/nmt/?request=GetHbyXY&x={x}&y={y} 22'
            r = urllib.request.urlopen(f'http://services.gugik.gov.pl/nmt/?request=GetHbyXY&x={x}&y={y}')
            return r.read().decode()
        except Exception as e:
            iface.messageBar().pushMessage('Wtyczka GUGiK NMT:', str(e), Qgis.Critical, 5)
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

    def coordsTransform(self, geom, epsg):
        activeCrs = QgsProject.instance().crs().authid()
        fromCrs = QgsCoordinateReferenceSystem(activeCrs)
        toCrs = QgsCoordinateReferenceSystem(epsg)
        transformation = QgsCoordinateTransform(fromCrs, toCrs, QgsProject.instance())
        geom = transformation.transform(geom)
        return geom

    def createTempLayer(self):
        if not self.savedFeats:
            iface.messageBar().pushMessage('Wtyczka GUGiK NMT:', 'Nie dodano punktów', Qgis.Warning, 5)
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
                #Jeśli nie ma aktywnego procesu to nic nie robimy
                pass
        self.tempLayer.dataProvider().addFeatures(features)
        self.tempLayer.updateExtents(True)
        self.identifyTool.tempGeom.reset(QgsWkbTypes.PointGeometry)
        del self.task

    def exportToCsv(self):
        path, _ = QFileDialog.getSaveFileName(filter=f'*.csv')
        if not path:
            return   
        rows = self.twData.rowCount()
        if not path.lower().endswith('.csv'):
            path += '.csv'
        if rows < 1:
            return
        with open(f'{path}', 'a') as f:
            for row in range(rows):
                data = f'{float(self.twData.item(row, 0).text())};{float(self.twData.item(row, 1).text())}\n'
                f.write(data)

    def cbLayerChanged(self):
        self.cbxUpdateField.setChecked(False)
        self.cbFields.clear()