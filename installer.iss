[Setup]
AppId={{A8B7C6D5-E4F3-2A1B-9C8D-7E6F5A4B3C2D}
AppName=AutoSwitcher
AppVersion=0.4.1
AppVerName=AutoSwitcher v0.4.1
AppPublisher=Antigravity
DefaultDirName={autopf}\AutoSwitcher
DefaultGroupName=AutoSwitcher
DisableProgramGroupPage=yes
OutputDir=.
OutputBaseFilename=AutoSwitcher_Setup_v0.4.1
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayName=AutoSwitcher
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"
Name: "startup"; Description: "Start AutoSwitcher when Windows starts"; GroupDescription: "Startup:"; Flags: checkedonce

[Files]
Source: "dist\AutoSwitcher_v0.4.1.exe"; DestDir: "{app}"; DestName: "AutoSwitcher.exe"; Flags: ignoreversion

[Icons]
Name: "{group}\AutoSwitcher"; Filename: "{app}\AutoSwitcher.exe"
Name: "{group}\Uninstall AutoSwitcher"; Filename: "{uninstallexe}"
Name: "{autodesktop}\AutoSwitcher"; Filename: "{app}\AutoSwitcher.exe"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "AutoSwitcher"; ValueData: """{app}\AutoSwitcher.exe"""; Flags: uninsdeletevalue; Tasks: startup

[Run]
Filename: "{app}\AutoSwitcher.exe"; Description: "Launch AutoSwitcher"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: files; Name: "{app}\config.json"
Type: files; Name: "{app}\debug.log"
Type: files; Name: "{app}\debug.log.*"
