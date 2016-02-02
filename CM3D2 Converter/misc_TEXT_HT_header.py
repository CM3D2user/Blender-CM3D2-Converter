import os, re, sys, bpy, time, bmesh, mathutils
from . import common

# メニュー等に項目追加
def menu_func(self, context):
	texts = bpy.data.texts
	text_keys = texts.keys()
	self.layout.label(text="CM3D2用:", icon_value=common.preview_collections['main']['KISS'].icon_id)
	row = self.layout.row(align=True)
	if 'BoneData' in text_keys:
		txt = bpy.data.texts['BoneData']
		line_count = 0
		for line in txt.as_string().split('\n'):
			if line:
				line_count += 1
		row.operator('text.show_text', icon='ARMATURE_DATA', text="BoneData (%d)" % line_count).name = 'BoneData'
	if 'LocalBoneData' in text_keys:
		txt = bpy.data.texts['LocalBoneData']
		line_count = 0
		for line in txt.as_string().split('\n'):
			if line:
				line_count += 1
		row.operator('text.show_text', icon='BONE_DATA', text="LocalBoneData (%d)" % line_count).name = 'LocalBoneData'
	if 'BoneData' in text_keys and 'LocalBoneData' in text_keys:
		if 'BoneData' in texts:
			if 'BaseBone' not in texts['BoneData']:
				texts['BoneData']['BaseBone'] = ""
			row.prop(texts['BoneData'], '["BaseBone"]', text="")
		row.operator('text.copy_text_bone_data', icon='COPYDOWN', text="")
		row.operator('text.paste_text_bone_data', icon='PASTEDOWN', text="")
	if 'Material:0' in text_keys:
		self.layout.label(text="", icon='MATERIAL_DATA')
		row = self.layout.row(align=True)
		pass_count = 0
		for i in range(99):
			name = "Material:" + str(i)
			if name in text_keys:
				sub_row = row.row(align=True)
				sub_row.scale_x = 0.5
				sub_row.operator('text.show_text', text=str(i)).name = name
			else:
				pass_count += 1
			if 9 < pass_count:
				break
		if "Material:0" in text_keys:
			row.operator('text.remove_all_material_texts', icon='X', text="")

class show_text(bpy.types.Operator):
	bl_idname = 'text.show_text'
	bl_label = "テキストを表示"
	bl_description = "指定したテキストをこの領域に表示します"
	bl_options = {'REGISTER', 'UNDO'}
	
	name = bpy.props.StringProperty(name="テキスト名")
	
	@classmethod
	def poll(cls, context):
		if 'text' in dir(context.space_data):
			return True
		return False
	
	def execute(self, context):
		context.space_data.text = bpy.data.texts[self.name]
		return {'FINISHED'}

class copy_text_bone_data(bpy.types.Operator):
	bl_idname = 'text.copy_text_bone_data'
	bl_label = "テキストのボーン情報をコピー"
	bl_description = "テキストのボーン情報をカスタムプロパティへ貼り付ける形にしてクリップボードにコピーします"
	bl_options = {'REGISTER', 'UNDO'}
	
	@classmethod
	def poll(cls, context):
		texts = context.blend_data.texts
		return 'BoneData' in texts and 'LocalBoneData' in texts
	
	def execute(self, context):
		output_text = ""
		if 'BaseBone' in context.blend_data.texts['BoneData']:
			output_text += "BaseBone:" + context.blend_data.texts['BoneData']['BaseBone'] + "\n"
		for line in context.blend_data.texts['BoneData'].as_string().split('\n'):
			if not line:
				continue
			output_text += "BoneData:" + line + "\n"
		for line in context.blend_data.texts['LocalBoneData'].as_string().split('\n'):
			if not line:
				continue
			output_text += "LocalBoneData:" + line + "\n"
		context.window_manager.clipboard = output_text
		self.report(type={'INFO'}, message="ボーン情報をクリップボードにコピーしました")
		return {'FINISHED'}

class paste_text_bone_data(bpy.types.Operator):
	bl_idname = 'text.paste_text_bone_data'
	bl_label = "テキストのボーン情報を貼り付け"
	bl_description = "クリップボード内のボーン情報をテキストデータに貼り付けます"
	bl_options = {'REGISTER', 'UNDO'}
	
	@classmethod
	def poll(cls, context):
		clipboard = context.window_manager.clipboard
		return 'BoneData:' in clipboard and 'LocalBoneData:' in clipboard
	
	def execute(self, context):
		import re
		clipboard = context.window_manager.clipboard
		if "BoneData" in context.blend_data.texts:
			bone_data_text = context.blend_data.texts["BoneData"]
			bone_data_text.clear()
		else:
			bone_data_text = context.blend_data.texts.new("BoneData")
		if "LocalBoneData" in context.blend_data.texts:
			local_bone_data_text = context.blend_data.texts["LocalBoneData"]
			local_bone_data_text.clear()
		else:
			local_bone_data_text = context.blend_data.texts.new("LocalBoneData")
		
		for line in context.window_manager.clipboard.split("\n"):
			r = re.search('^BaseBone:(.+)$', line)
			if r:
				bone_data_text['BaseBone'] = r.groups()[0]
				local_bone_data_text['BaseBone'] = r.groups()[0]
			r = re.search('^BoneData:(.+)$', line)
			if r:
				if line.count(',') == 4:
					info = r.groups()[0]
					bone_data_text.write(info + "\n")
			r = re.search('^LocalBoneData:(.+)$', line)
			if r:
				if line.count(',') == 1:
					info = r.groups()[0]
					local_bone_data_text.write(info + "\n")
		bone_data_text.current_line_index = 0
		local_bone_data_text.current_line_index = 0
		self.report(type={'INFO'}, message="ボーン情報をクリップボードから貼り付けました")
		return {'FINISHED'}

class remove_all_material_texts(bpy.types.Operator):
	bl_idname = 'text.remove_all_material_texts'
	bl_label = "マテリアル情報テキストを全削除"
	bl_description = "CM3D2で使用できるマテリアルテキストを全て削除します"
	bl_options = {'REGISTER', 'UNDO'}
	
	is_keep_used_material = bpy.props.BoolProperty(name="使用する分は保管", default=True)
	
	@classmethod
	def poll(cls, context):
		return 'Material:0' in context.blend_data.texts
	
	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		self.layout.prop(self, 'is_keep_used_material')
	
	def execute(self, context):
		remove_texts = []
		pass_count = 0
		for i in range(9999):
			name = 'Material:' + str(i)
			if name in context.blend_data.texts:
				remove_texts.append(context.blend_data.texts[name])
			else:
				pass_count += 1
			if 10 < pass_count:
				break
		if self.is_keep_used_material:
			ob = context.active_object
			if ob:
				remove_texts = remove_texts[len(ob.material_slots):]
		for txt in remove_texts:
			context.blend_data.texts.remove(txt)
		return {'FINISHED'}
