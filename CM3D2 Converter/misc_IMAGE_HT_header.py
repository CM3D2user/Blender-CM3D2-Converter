# 「UV/画像エディター」エリア → ヘッダー
import os, re, sys, bpy, time, bmesh, mathutils
from . import common

# メニュー等に項目追加
def menu_func(self, context):
	if 'edit_image' in dir(context):
		img = context.edit_image
		if img:
			if 'cm3d2_path' in img:
				self.layout.label(text="CM3D2用: 内部パス", icon_value=common.preview_collections['main']['KISS'].icon_id)
				row = self.layout.row()
				row.prop(img, '["cm3d2_path"]', text="")
				row.scale_x = 3.0
