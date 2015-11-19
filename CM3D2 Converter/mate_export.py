import os, re, bpy, struct, os.path, shutil

def ArrangeName(name, flag=True):
	if flag:
		return re.sub(r'\.\d{3}$', "", name)
	return name

def WriteStr(file, s):
	str_count = len(s.encode('utf-8'))
	if 128 <= str_count:
		b = (str_count % 128) + 128
		file.write(struct.pack('<B', b))
		b = str_count // 128
		file.write(struct.pack('<B', b))
	else:
		file.write(struct.pack('<B', str_count))
	file.write(s.encode('utf-8'))

class text_export_mate(bpy.types.Operator):
	bl_idname = 'text.text_export_mate'
	bl_label = "mateとして保存"
	bl_description = "表示しているテキストデータをmateファイルとして保存します"
	bl_options = {'REGISTER', 'UNDO'}
	
	filepath = bpy.props.StringProperty(subtype='FILE_PATH')
	filename_ext = ".mate"
	filter_glob = bpy.props.StringProperty(default="*.mate", options={'HIDDEN'})
	
	is_backup = bpy.props.BoolProperty(name="ファイルをバックアップ", default=True, description="ファイルに上書きする場合にバックアップファイルを複製します")
	
	version = bpy.props.IntProperty(name="ファイルバージョン", default=1000, min=1000, max=1111, soft_min=1000, soft_max=1111, step=1)
	
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
		if not context.user_preferences.addons[__name__.split('.')[0]].preferences.mate_export_path:
			try:
				import winreg
				with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\KISS\カスタムメイド3D2') as key:
					path = winreg.QueryValueEx(key, 'InstallPath')[0]
					path = os.path.join(path, 'GameData', '*.mate')
					context.user_preferences.addons[__name__.split('.')[0]].preferences.mate_export_path = path
			except:
				pass
		head, tail = os.path.split(context.user_preferences.addons[__name__.split('.')[0]].preferences.mate_export_path)
		if lines[2] and lines[2] != '***':
			self.filepath = os.path.join(head, lines[2])
		else:
			self.filepath = os.path.join(head, txt.name)
		root, ext = os.path.splitext(self.filepath)
		self.filepath = root + ".mate"
		try:
			self.version = int(lines[0])
		except:
			self.version = 1000
		context.window_manager.fileselect_add(self)
		return {'RUNNING_MODAL'}
	
	def draw(self, context):
		row = self.layout.row()
		row.prop(self, 'is_backup', icon='FILE_BACKUP')
		if not context.user_preferences.addons[__name__.split('.')[0]].preferences.backup_ext:
			row.enabled = False
		self.layout.prop(self, 'version', icon='LINENUMBERS_ON')
	
	def execute(self, context):
		context.user_preferences.addons[__name__.split('.')[0]].preferences.mate_export_path = self.filepath
		
		# バックアップ
		if self.is_backup and context.user_preferences.addons[__name__.split('.')[0]].preferences.backup_ext:
			if os.path.exists(self.filepath):
				backup_path = self.filepath + "." + context.user_preferences.addons[__name__.split('.')[0]].preferences.backup_ext
				shutil.copyfile(self.filepath, backup_path)
				self.report(type={'INFO'}, message="上書き時にバックアップを複製しました")
		
		txt = context.edit_text
		lines = txt.as_string().split('\n')
		
		file = open(self.filepath, 'wb')
		WriteStr(file, 'CM3D2_MATERIAL')
		file.write(struct.pack('<i', self.version))
		
		if lines[1] != '***':
			WriteStr(file, lines[1])
		else:
			WriteStr(file, lines[2])
		WriteStr(file, lines[2])
		WriteStr(file, lines[3])
		WriteStr(file, lines[4])
		
		line_seek = 5
		try:
			for i in range(99999):
				if len(lines) <= line_seek:
					break
				if not lines[line_seek]:
					line_seek += 1
					continue
				if lines[line_seek] == 'tex':
					WriteStr(file, lines[line_seek])
					WriteStr(file, lines[line_seek + 1].replace('\t', ''))
					WriteStr(file, lines[line_seek + 2].replace('\t', ''))
					line_seek += 3
					if lines[line_seek - 1].replace('\t', '') == 'tex2d':
						WriteStr(file, lines[line_seek].replace('\t', ''))
						WriteStr(file, lines[line_seek + 1].replace('\t', ''))
						floats = lines[line_seek + 2].replace('\t', '').split(' ')
						for f in floats:
							file.write(struct.pack('<f', float(f)))
						line_seek += 3
				elif lines[line_seek] == 'col':
					WriteStr(file, lines[line_seek])
					WriteStr(file, lines[line_seek + 1].replace('\t', ''))
					floats = lines[line_seek + 2].replace('\t', '').split(' ')
					for f in floats:
						file.write(struct.pack('<f', float(f)))
					line_seek += 3
				elif lines[line_seek] == 'f':
					WriteStr(file, lines[line_seek])
					WriteStr(file, lines[line_seek + 1].replace('\t', ''))
					f = float(lines[line_seek + 2].replace('\t', ''))
					file.write(struct.pack('<f', f))
					line_seek += 3
				else:
					self.report(type={'ERROR'}, message="tex col f 以外の設定値が見つかりました(" + lines[line_seek] + ")、中止します")
					return {'CANCELLED'}
		except:
			self.report(type={'ERROR'}, message="mateファイルの出力に失敗、中止します。 構文を見直して下さい")
			return {'CANCELLED'}
		WriteStr(file, 'end')
		
		file.close()
		return {'FINISHED'}

# テキストメニューに項目を登録
def TEXT_MT_text(self, context):
	self.layout.operator(text_export_mate.bl_idname, icon='SPACE2')
