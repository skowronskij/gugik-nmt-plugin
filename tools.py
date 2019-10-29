# -*- coding: utf-8 -*-

from qgis.PyQt.QtGui import QCursor, QPixmap
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
        print(height)
        if height:
            self.parent.dbsHeight.setValue(float(height))

