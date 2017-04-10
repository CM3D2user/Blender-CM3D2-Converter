# 「3Dビュー」エリア → 追加(Shift+A) → CM3D2
import os, re, sys, bpy, time, bmesh, mathutils
from . import common

# メニュー等に項目追加
def menu_func(self, context):
	self.layout.separator()
	self.layout.menu('misc_INFO_MT_add_cm3d2', icon_value=common.preview_collections['main']['KISS'].icon_id)

# サブメニュー
class misc_INFO_MT_add_cm3d2(bpy.types.Menu):
	bl_idname = 'misc_INFO_MT_add_cm3d2'
	bl_label = "CM3D2"
	
	def draw(self, context):
		self.layout.operator('wm.append_cm3d2_figure', text="body001", icon_value=common.preview_collections['main']['KISS'].icon_id).object_name = "body001.body"
		self.layout.separator()
		self.layout.operator('wm.append_cm3d2_figure', text="乳袋防止素体", icon='ROTATECOLLECTION').object_name = "乳袋防止素体"
		self.layout.separator()
		self.layout.operator('wm.append_cm3d2_figure', text="Tスタンス素体", icon='ARMATURE_DATA').object_name = "Tスタンス素体"
		self.layout.operator('wm.append_cm3d2_figure', text="Tスタンス素体 足のみ", icon='SOUND').object_name = "Tスタンス素体 足のみ"
		self.layout.operator('wm.append_cm3d2_figure', text="Tスタンス素体 手のみ", icon='OUTLINER_DATA_ARMATURE').object_name = "Tスタンス素体 手のみ"
		self.layout.separator()
		self.layout.operator('wm.append_cm3d2_figure', text="anm出力用リグ", icon='OUTLINER_OB_ARMATURE').object_name = "anm出力用リグ・身体メッシュ"
		self.layout.operator('wm.append_cm3d2_figure', text="anm出力用リグ(男)", icon='MOD_ARMATURE').object_name = "anm出力用リグ(男)・身体メッシュ"

class append_cm3d2_figure(bpy.types.Operator):
	bl_idname = 'wm.append_cm3d2_figure'
	bl_label = "CM3D2用の素体をインポート"
	bl_description = "CM3D2関係の素体を現在のシーンにインポートします"
	bl_options = {'REGISTER', 'UNDO'}
	
	object_name = bpy.props.StringProperty(name="素体名")
	
	def execute(self, context):
		if bpy.ops.object.mode_set.poll():
			bpy.ops.object.mode_set(mode='OBJECT')
		if bpy.ops.object.select_all.poll():
			bpy.ops.object.select_all(action='DESELECT')
		
		blend_path = os.path.join(os.path.dirname(__file__), "append_data.blend")
		with context.blend_data.libraries.load(blend_path) as (data_from, data_to):
			data_to.objects = [self.object_name]
		
		ob = data_to.objects[0]
		context.scene.objects.link(ob)
		context.scene.objects.active = ob
		ob.select = True
		
		for mod in ob.modifiers:
			if mod.type == 'ARMATURE':
				context.scene.objects.link(mod.object)
				mod.object.select = True
		
		return {'FINISHED'}
