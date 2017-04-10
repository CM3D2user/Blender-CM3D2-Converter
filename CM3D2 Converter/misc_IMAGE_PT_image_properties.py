# 「UV/画像エディター」エリア → プロパティ → 「画像」パネル
import os, re, sys, bpy, time, bmesh, mathutils
from . import common

# メニュー等に項目追加
def menu_func(self, context):
	if 'edit_image' in dir(context):
		img = context.edit_image
		if 'cm3d2_path' in img:
			box = self.layout.box()
			box.label(text="CM3D2用", icon_value=common.preview_collections['main']['KISS'].icon_id)
			box.prop(img, '["cm3d2_path"]', icon='ANIM_DATA', text="内部パス")
