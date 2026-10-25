' windows-codex-context-meter-float.vbs — 双击启动悬浮窗，无控制台黑窗
Set sh = CreateObject("WScript.Shell")
dir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = dir
sh.Run "pythonw """ & dir & "\windows-codex-context-meter-float.py""", 0, False
