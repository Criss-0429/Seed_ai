#define AppName "SEED"
#ifndef AppVersion
  #define AppVersion "0.3.0-pilot"
#endif
#ifndef ReleaseRoot
  #define ReleaseRoot "..\release\" + AppVersion
#endif

[Setup]
AppId={{599D3FD4-1146-48AD-9D84-E17D8FD7D93C}
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\SEED
DefaultGroupName=SEED
OutputDir={#ReleaseRoot}
OutputBaseFilename=SEED-{#AppVersion}-Setup-Unsigned
Compression=lzma2/ultra64
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayName=SEED
DisableProgramGroupPage=yes
WizardStyle=modern
InfoBeforeFile=TESTER_GUIDE.md
UsePreviousAppDir=yes
CloseApplications=yes
RestartApplications=no

[Files]
Source: "{#ReleaseRoot}\app\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#ReleaseRoot}\release-manifest.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ReleaseRoot}\TESTER_GUIDE.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\SEED"; Filename: "{app}\supervisor\SEEDSupervisor.exe"; Parameters: "--boot --runtime ""{app}\runtime\SEED.exe"""
Name: "{autodesktop}\SEED"; Filename: "{app}\supervisor\SEEDSupervisor.exe"; Parameters: "--boot --runtime ""{app}\runtime\SEED.exe"""; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Crea collegamento sul desktop"; GroupDescription: "Collegamenti:"

[Run]
Filename: "{app}\supervisor\SEEDSupervisor.exe"; Parameters: "--boot --runtime ""{app}\runtime\SEED.exe"""; Description: "Avvia SEED tramite supervisor"; Flags: nowait postinstall skipifsilent

[Code]
var
  RemoveData: Boolean;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssInstall then
    ForceDirectories(ExpandConstant('{localappdata}\SEED\core_config'));
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
    RemoveData := MsgBox(
      'Vuoi eliminare anche memoria, configurazione, credenziali cifrate, lineage e backup locali di SEED?'#13#10#13#10 +
      'Scegli No per conservare i dati.',
      mbConfirmation, MB_YESNO) = IDYES;
  if (CurUninstallStep = usPostUninstall) and RemoveData then
    DelTree(ExpandConstant('{localappdata}\SEED'), True, True, True);
end;
