; Inno Setup script for Lmonitor (Inno Setup 6.3 or newer)
; Built by build_installer_qt.bat:
;   ISCC /DAppVersion=x.y.z [/DSourceDir=...] installer\Lmonitor.iss
;
; Settings live in %APPDATA%\Lmonitor. The installer never writes there and
; the uninstaller keeps it unless the user explicitly chooses to delete it.

#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#define AppName "Lmonitor"
#define AppExe  "Lmonitor.exe"
#ifndef SourceDir
  #define SourceDir "..\_build\dist\Lmonitor"
#endif

[Setup]
; Never change AppId: it is how a new version finds and upgrades the old one.
AppId={{6E1F4B52-9C0A-4D5B-8E37-2A7C91D4F0B3}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppName}
VersionInfoVersion={#AppVersion}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\_output
OutputBaseFilename=Lmonitor_Setup_{#AppVersion}
SetupIconFile=..\Lmonitor.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; the program is running (overlay/tray): close it for the update
AppMutex=LmonitorOverlay
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
; the driver is shared with other tools and is never removed by our uninstaller
Name: "pawnio"; Description: "Install the PawnIO driver (needed for CPU temperature and power)"; GroupDescription: "Sensors:"; Check: not PawnIoInstalled

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; official PawnIO installer (run silently below, then removed from the temp folder)
Source: "..\PawnIO_setup.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall; Tasks: pawnio

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"; IconFilename: "{app}\{#AppExe}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; IconFilename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
; shellexec: the program asks for administrator rights itself (UAC)
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent shellexec

[UninstallRun]
Filename: "{sys}\taskkill.exe"; Parameters: "/F /IM {#AppExe}"; Flags: runhidden; RunOnceId: "KillLmonitor"
; the "Start with Windows" task (if the user switched it on)
Filename: "{sys}\schtasks.exe"; Parameters: "/Delete /TN ""Lmonitor"" /F"; Flags: runhidden; RunOnceId: "LmonitorTask"

[Code]
function PawnIoInstalled(): Boolean;
begin
  { key used by the PawnIO installer itself (Add/Remove Programs entry) }
  Result := RegKeyExists(HKLM, 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\PawnIO');
end;

{ MSI Afterburner's overlay (RivaTuner Statistics Server) hooks every DirectX program,
  Lmonitor too. RivaTuner's own "do not hook" profile for Lmonitor.exe keeps the two apart
  (the same kind of profile RivaTuner ships for HWiNFO and Discord). }
function RtssDir(): String;
begin
  Result := '';
  if not RegQueryStringValue(HKLM32, 'SOFTWARE\Unwinder\RTSS', 'InstallDir', Result) then
    RegQueryStringValue(HKLM64, 'SOFTWARE\Unwinder\RTSS', 'InstallDir', Result);
  if (Result <> '') and not DirExists(Result + '\Profiles') then
    Result := '';
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  Code: Integer;
  Ran: Boolean;
begin
  if (CurStep = ssPostInstall) and (RtssDir() <> '') and not FileExists(RtssDir() + '\Profiles\{#AppExe}.cfg') then
    SaveStringToFile(RtssDir() + '\Profiles\{#AppExe}.cfg', '[Hooking]' + #13#10 + 'EnableHooking' + #9#9 + '= 0' + #13#10, False);
  if (CurStep = ssPostInstall) and WizardIsTaskSelected('pawnio') then
  begin
    WizardForm.StatusLabel.Caption := 'Installing the PawnIO driver...';
    Ran := Exec(ExpandConstant('{tmp}\PawnIO_setup.exe'), '-install -silent', '',
                SW_HIDE, ewWaitUntilTerminated, Code);
    if Ran and (Code = 0) then
      Log('PawnIO installed')
    else if Ran and (Code = 3010) then
      SuppressibleMsgBox('The PawnIO driver is installed. Restart Windows if CPU temperature stays empty.',
                         mbInformation, MB_OK, IDOK)
    else
      SuppressibleMsgBox('The PawnIO driver could not be installed (code ' + IntToStr(Code) + ').' + #13#10 +
                         'Lmonitor still works, but CPU temperature and power will be missing.' + #13#10 +
                         'You can retry later from the yellow message inside Lmonitor.',
                         mbError, MB_OK, IDOK);
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Dir: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    if RtssDir() <> '' then                       { the RivaTuner profile made at install }
      DeleteFile(RtssDir() + '\Profiles\{#AppExe}.cfg');
    Dir := ExpandConstant('{userappdata}\Lmonitor');
    { default = keep. A silent uninstall never deletes settings. }
    if (not UninstallSilent) and DirExists(Dir) then
      if MsgBox('Also delete your Lmonitor settings and error log?' + #13#10 +
                Dir + #13#10#13#10 + 'Choose No to keep them for a later install.',
                mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
        DelTree(Dir, True, True, True);
  end;
end;
