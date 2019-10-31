# -*- coding: utf-8 -*-

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QCursor, QPixmap, QColor
from qgis.core import QgsMapLayer, QgsWkbTypes, QgsGeometry, QgsProject
from qgis.gui import QgsRubberBand, QgsMapTool
from qgis.utils import iface

class BaseTool(QgsMapTool):
    """ Klasa bazowe narzędzi """
    def __init__(self, parent):
        canvas = iface.mapCanvas()
        super(BaseTool, self).__init__(canvas)
        self.parent = parent
        
        self.setCursor( QCursor(QPixmap(["16 16 2 1",
                        "      c None",
                        ".     c #000000",
                        "                ",
                        "        .       ",
                        "        .       ",
                        "      .....     ",
                        "     .     .    ",
                        "    .   .   .   ",
                        "   .    .    .  ",
                        "   .    .    .  ",
                        " ... ... ... ...",
                        "   .    .    .  ",
                        "   .    .    .  ",
                        "    .   .   .   ",
                        "     .     .    ",
                        "      .....     ",
                        "        .       ",
                        "        .       "])) )

        self.tempGeom = QgsRubberBand(canvas, QgsWkbTypes.PointGeometry)
        self.tempGeom.setColor(QColor('red'))
        self.tempGeom.setIconSize = 5
        
    def canvasMoveEvent(self, e):
        if QgsProject.instance().crs().authid() != 'EPSG:2180':
            point92 = self.parent.coordsTransform(e.mapPoint(), 'EPSG:2180')
        else:
            point92 = e.mapPoint()
        if QgsProject.instance().crs().authid() != 'EPSG:4326':
            point84 = self.parent.coordsTransform(e.mapPoint(), 'EPSG:4326')
        else:
            point84 = e.mapPoint()
        x92, y92 = point92.x(), point92.y()
        x84, y84 = point84.x(), point84.y()
        self.parent.dbs92X.setValue(x92)
        self.parent.dbs92Y.setValue(y92)
        self.parent.dsbWgsX.setValue(x84)
        self.parent.dsbWgsY.setValue(y84)

    def canvasReleaseEvent(self, e):
        geom = QgsGeometry.fromPointXY(e.mapPoint())
        height = self.parent.getHeight(geom)
        if height:
            self.parent.dbsHeight.setValue(float(height))
            self.tempGeom.addPoint(e.mapPoint())
            self.parent.savedFeats.append({
                'geometry':geom, 
                'height':height
                })

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.tempGeom.reset(QgsWkbTypes.PointGeometry)
            if self.parent.savedFeats:
                self.parent.savedFeats = []
        elif e.key() == Qt.Key_Delete:
            self.tempGeom.removeLastPoint()
            if self.parent.savedFeats:
                del self.parent.savedFeats[-1]
