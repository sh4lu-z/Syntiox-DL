[Setup]
AppId={{9F5768B2-16BC-4A29-87D2-7E1A1BDE1A5F}
AppName=Syntiox DL
AppVersion=1.0.0
AppPublisher=Syntiox / sh4lu-z
AppPublisherURL=https://github.com/sh4lu-z/Syntiox-DL
AppSupportURL=https://github.com/sh4lu-z/Syntiox-DL/issues
AppUpdatesURL=https://github.com/sh4lu-z/Syntiox-DL/releases
DefaultDirName={autopf}\Syntiox DL
DisableProgramGroupPage=yes
LicenseFile=LICENSE.txt
OutputDir=dist
OutputBaseFilename=Syntiox DL
SetupIconFile=assets\icon.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\Syntiox-DL.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Syntiox DL"; Filename: "{app}\Syntiox-DL.exe"
Name: "{autoprograms}\Uninstall Syntiox DL"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Syntiox DL"; Filename: "{app}\Syntiox-DL.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Syntiox-DL.exe"; Description: "{cm:LaunchProgram,Syntiox DL}"; Flags: nowait postinstall skipifsilent
