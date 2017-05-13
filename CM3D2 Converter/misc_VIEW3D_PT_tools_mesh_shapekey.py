# 「3Dビュー」エリア → 「メッシュエディット」モード → ツールシェルフ → 「シェイプキーツール」パネル
import os, re, sys, bpy, time, bmesh, mathutils
from . import common

"""
class VIEW3D_PT_tools_mesh_shapekey(bpy.types.Panel):
	bl_label = "シェイプキーツール"
	bl_idname = 'VIEW3D_PT_tools_mesh_shapekey'
	bl_region_type = 'TOOLS'
	bl_space_type = 'VIEW_3D'
	bl_category = 'Tools'
	bl_context = 'mesh_edit'
	
	def draw(self, context):
		pass
"""
