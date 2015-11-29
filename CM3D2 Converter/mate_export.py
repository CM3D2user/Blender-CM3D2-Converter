import os, re, bpy, struct, os.path, shutil
from . import common

class export_cm3d2_mate(bpy.types.Operator):
	bl_idname = 'material.export_cm3d2_mate'
	bl_label = "mateとして保存"
	bl_description = "表示しているマテリアルをmateファイルとして保存します"
	bl_options = {'REGISTER', 'UNDO'}
	
	filepath = bpy.props.StringProperty(subtype='FILE_PATH')
	filename_ext = ".mate"
	filter_glob = bpy.props.StringProperty(default="*.mate", options={'HIDDEN'})
	
	is_backup = bpy.props.BoolProperty(name="ファイルをバックアップ", default=True, description="ファイルに上書きする場合にバックアップファイルを複製します")
	
	version = bpy.props.IntProperty(name="ファイルバージョン", default=1000, min=1000, max=1111, soft_min=1000, soft_max=1111, step=1)
	name1 = bpy.props.StringProperty(name="名前1")
	name2 = bpy.props.StringProperty(name="名前2")
	
	@classmethod
	def poll(cls, context):
		if 'material' in dir(context):
			mate = context.material
			if mate:
				if 'shader1' in mate.keys() and 'shader2' in mate.keys():
					return True
		return False
	
	def invoke(self, context, event):
		mate = context.material
		self.filepath = common.default_cm3d2_dir(common.preferences().mate_export_path, mate.name.lower(), "mate")
		self.is_backup = bool(common.preferences().backup_ext)
		self.name1 = common.remove_serial_number(mate.name.lower())
		self.name2 = common.remove_serial_number(mate.name)
		context.window_manager.fileselect_add(self)
		return {'RUNNING_MODAL'}
	
	def draw(self, context):
		row = self.layout.row()
		row.prop(self, 'is_backup', icon='FILE_BACKUP')
		if not common.preferences().backup_ext:
			row.enabled = False
		self.layout.prop(self, 'version', icon='LINENUMBERS_ON')
		self.layout.prop(self, 'name1', icon='SORTALPHA')
		self.layout.prop(self, 'name2', icon='SORTALPHA')
	
	def execute(self, context):
		common.preferences().mate_export_path = self.filepath
		
		# バックアップ
		common.file_backup(self.filepath, self.is_backup)
		
		mate = context.material
		
		try:
			file = open(self.filepath, 'wb')
		except:
			self.report(type={'ERROR'}, message="ファイルを開くのに失敗しました、アクセス不可の可能性があります")
			return {'CANCELLED'}
		common.write_str(file, 'CM3D2_MATERIAL')
		file.write(struct.pack('<i', self.version))
		
		common.write_str(file, self.name1)
		common.write_str(file, self.name2)
		common.write_str(file, mate['shader1'])
		common.write_str(file, mate['shader2'])
		
		for tex_slot in mate.texture_slots:
			if not tex_slot:
				continue
			tex = tex_slot.texture
			if tex_slot.use:
				type = 'tex'
			else:
				if tex_slot.use_rgb_to_intensity:
					type = 'col'
				else:
					type = 'f'
			common.write_str(file, type)
			common.write_str(file, common.remove_serial_number(tex.name))
			if type == 'tex':
				try:
					img = tex.image
				except:
					self.report(type={'ERROR'}, message="texタイプの設定値の取得に失敗しました、中止します")
					return {'CANCELLED'}
				if img:
					common.write_str(file, 'tex2d')
					common.write_str(file, common.remove_serial_number(img.name))
					if 'cm3d2_path' in img.keys():
						path = img['cm3d2_path']
					else:
						path = img.filepath
					path = path.replace('\\', '/')
					path = re.sub(r'^[\/\.]*', "", path)
					if not re.search(r'^assets/texture/', path, re.I):
						path = "Assets/texture/texture/" + os.path.basename(path)
					common.write_str(file, path)
					col = tex_slot.color
					file.write(struct.pack('<3f', col[0], col[1], col[2]))
					file.write(struct.pack('<f', tex_slot.diffuse_color_factor))
				else:
					common.write_str(file, 'null')
			elif type == 'col':
				col = tex_slot.color
				file.write(struct.pack('<3f', col[0], col[1], col[2]))
				file.write(struct.pack('<f', tex_slot.diffuse_color_factor))
			elif type == 'f':
				file.write(struct.pack('<f', tex_slot.diffuse_color_factor))
		
		common.write_str(file, 'end')
		file.close()
		return {'FINISHED'}

class export_cm3d2_mate_text(bpy.types.Operator):
	bl_idname = 'text.export_cm3d2_mate_text'
	bl_label = "mateとして保存"
	bl_description = "表示しているテキストデータをmateファイルとして保存します"
	bl_options = {'REGISTER', 'UNDO'}
	
	filepath = bpy.props.StringProperty(subtype='FILE_PATH')
	filename_ext = ".mate"
	filter_glob = bpy.props.StringProperty(default="*.mate", options={'HIDDEN'})
	
	is_backup = bpy.props.BoolProperty(name="ファイルをバックアップ", default=True, description="ファイルに上書きする場合にバックアップファイルを複製します")
	
	version = bpy.props.IntProperty(name="ファイルバージョン", default=1000, min=1000, max=1111, soft_min=1000, soft_max=1111, step=1)
	name1 = bpy.props.StringProperty(name="名前1")
	name2 = bpy.props.StringProperty(name="名前2")
	
	@classmethod
	def poll(cls, context):
		if 'edit_text' in dir(context):
			txt = context.edit_text
			if txt:
				data = txt.as_string()
				lines = txt.as_string().split('\n')
				if len(lines) < 10:
					return False
				match_strs = ['\ntex\n', '\ncol\n', '\nf\n', '\n\t_MainTex\n', '\n\t_Color\n', '\n\t_Shininess\n']
				for s in match_strs:
					if s in data:
						return True
		return False
	
	def invoke(self, context, event):
		txt = context.edit_text
		lines = txt.as_string().split('\n')
		self.filepath = common.default_cm3d2_dir(common.preferences().mate_export_path, lines[1], "mate")
		try:
			self.version = int(lines[0])
		except:
			self.version = 1000
		if lines[1] != '***':
			self.name1 = lines[1]
		else:
			self.name1 = lines[2]
		self.name2 = lines[2]
		context.window_manager.fileselect_add(self)
		return {'RUNNING_MODAL'}
	
	def draw(self, context):
		row = self.layout.row()
		row.prop(self, 'is_backup', icon='FILE_BACKUP')
		if not common.preferences().backup_ext:
			row.enabled = False
		self.layout.prop(self, 'version', icon='LINENUMBERS_ON')
		self.layout.prop(self, 'name1', icon='SORTALPHA')
		self.layout.prop(self, 'name2', icon='SORTALPHA')
	
	def execute(self, context):
		common.preferences().mate_export_path = self.filepath
		
		# バックアップ
		common.file_backup(self.filepath, self.is_backup)
		
		txt = context.edit_text
		lines = txt.as_string().split('\n')
		
		try:
			file = open(self.filepath, 'wb')
		except:
			self.report(type={'ERROR'}, message="ファイルを開くのに失敗しました、アクセス不可の可能性があります")
			return {'CANCELLED'}
		
		common.write_str(file, 'CM3D2_MATERIAL')
		file.write(struct.pack('<i', self.version))
		
		common.write_str(file, self.name1)
		common.write_str(file, self.name2)
		common.write_str(file, lines[3])
		common.write_str(file, lines[4])
		
		line_seek = 5
		try:
			for i in range(99999):
				if len(lines) <= line_seek:
					break
				if not lines[line_seek]:
					line_seek += 1
					continue
				if lines[line_seek] == 'tex':
					common.write_str(file, common.line_trim(lines[line_seek]))
					common.write_str(file, common.line_trim(lines[line_seek + 1]))
					common.write_str(file, common.line_trim(lines[line_seek + 2]))
					line_seek += 3
					if common.line_trim(lines[line_seek - 1]) == 'tex2d':
						common.write_str(file, common.line_trim(lines[line_seek]))
						common.write_str(file, common.line_trim(lines[line_seek + 1]))
						floats = common.line_trim(lines[line_seek + 2]).split(' ')
						for f in floats:
							file.write(struct.pack('<f', float(f)))
						line_seek += 3
				elif lines[line_seek] == 'col':
					common.write_str(file, common.line_trim(lines[line_seek]))
					common.write_str(file, common.line_trim(lines[line_seek + 1]))
					floats = common.line_trim(lines[line_seek + 2]).split(' ')
					for f in floats:
						file.write(struct.pack('<f', float(f)))
					line_seek += 3
				elif lines[line_seek] == 'f':
					common.write_str(file, common.line_trim(lines[line_seek]))
					common.write_str(file, common.line_trim(lines[line_seek + 1]))
					f = float(common.line_trim(lines[line_seek + 2]))
					file.write(struct.pack('<f', f))
					line_seek += 3
				else:
					self.report(type={'ERROR'}, message="tex col f 以外の設定値が見つかりました、中止します")
					return {'CANCELLED'}
		except:
			self.report(type={'ERROR'}, message="mateファイルの出力に失敗、中止します。 構文を見直して下さい")
			return {'CANCELLED'}
		common.write_str(file, 'end')
		
		file.close()
		return {'FINISHED'}

# テキストメニューに項目を登録
def TEXT_MT_text(self, context):
	self.layout.operator(export_cm3d2_mate_text.bl_idname, icon_value=common.preview_collections['main']['KISS'].icon_id)
