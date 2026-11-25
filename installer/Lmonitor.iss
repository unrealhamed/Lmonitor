; Inno Setup script for Lmonitor (Inno Setup 6.3 or newer)
; Built by build_installer_qt.bat:
;   ISCC /DAppVersion=x.y.z [/DSourceDir=...] installer\Lmonitor.iss
;
; Settings live in %APPDATA%\Lmonitor. The installer never writes there and
; the uninstaller keeps it unless the user explicitly chooses to delete it.

#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#ifndef AppName
  #define AppName "Lmonitor"
#endif
#define AppExe  "Lmonitor.exe"
#ifndef SourceDir
  #define SourceDir "..\_build\dist\Lmonitor"
#endif

#ifndef AppIdValue
  ; Never change AppId: it is how a new version finds and upgrades the old one.
  ; (Only a test build may set another one, so it can be installed next to the real one.)
  #define AppIdValue "{{6E1F4B52-9C0A-4D5B-8E37-2A7C91D4F0B3}"
#endif

[Setup]
AppId={#AppIdValue}
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
; Lmonitor's look: the Windows 11 style, light or dark like Windows itself, with Lmonitor's own
; background in dark mode and its own pictures (made by tools/make_installer_art.py)
WizardStyle=modern dynamic windows11 hidebevels
WizardBackColorDynamicDark=#0E1014
WizardImageFile=art\wizard-164x314.bmp,art\wizard-192x386.bmp,art\wizard-246x459.bmp,art\wizard-273x556.bmp,art\wizard-328x604.bmp,art\wizard-355x700.bmp,art\wizard-410x797.bmp
WizardImageStretch=no
WizardImageBackColor=#0E1014
WizardSmallImageFile=art\small-55x55.bmp,art\small-64x68.bmp,art\small-83x80.bmp,art\small-92x97.bmp,art\small-110x106.bmp,art\small-119x123.bmp,art\small-138x140.bmp
; in dark mode Windows-style Setup swaps in its own pictures unless these are given
WizardImageFileDynamicDark=art\wizard-164x314.bmp,art\wizard-192x386.bmp,art\wizard-246x459.bmp,art\wizard-273x556.bmp,art\wizard-328x604.bmp,art\wizard-355x700.bmp,art\wizard-410x797.bmp
WizardSmallImageFileDynamicDark=art\small-dark-55x55.bmp,art\small-dark-64x68.bmp,art\small-dark-83x80.bmp,art\small-dark-92x97.bmp,art\small-dark-110x106.bmp,art\small-dark-119x123.bmp,art\small-dark-138x140.bmp
; few pages: welcome, folder (only on a first install), options, progress, done
DisableWelcomePage=no
DisableReadyPage=yes
DisableDirPage=auto
ShowLanguageDialog=no
; the program is running (overlay/tray): close it for the update
AppMutex=LmonitorOverlay
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Messages]
WelcomeLabel1=Welcome to Lmonitor
WelcomeLabel2=Lmonitor shows your FPS, temperatures and more on top of your games, and tells you in plain words how your PC is doing.%n%nSetup takes about a minute. If Lmonitor is open, it is closed for the update and your settings are kept.
FinishedHeadingLabel=Lmonitor is ready
FinishedLabelNoIcons=Lmonitor is installed. You find it in the Start menu.
FinishedLabel=Lmonitor is installed. You find it in the Start menu.
SelectTasksDesc=Pick what you want - you can change it later.
SelectTasksLabel2=
ClickNext=Click Next to continue.
WizardSelectTasks=Options
ButtonFinish=&Done
StatusExtractFiles=Copying Lmonitor's files...
SetupAppTitle=Lmonitor setup
SetupWindowTitle=Lmonitor %1 setup
UninstallAppTitle=Remove Lmonitor
UninstallAppFullTitle=Remove %1
ConfirmUninstall=Remove Lmonitor from this PC?%n%nYou are asked next whether to keep your settings and game history.
UninstalledAll=Lmonitor was removed from this PC.

[Tasks]
Name: "desktopicon"; Description: "Put a Lmonitor icon on the desktop"; GroupDescription: "Shortcuts:"; Flags: unchecked
; the driver is shared with other tools and is never removed by our uninstaller
Name: "pawnio"; Description: "Install the PawnIO driver - needed to show CPU temperature and power (recommended)"; GroupDescription: "Sensors:"; Check: not PawnIoInstalled

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
#ifdef TestBuild
Filename: "{app}\{#AppExe}"; Description: "Open Lmonitor now"; Flags: nowait postinstall skipifsilent shellexec unchecked
#else
Filename: "{app}\{#AppExe}"; Description: "Open Lmonitor now"; Flags: nowait postinstall skipifsilent shellexec
#endif

#ifndef TestBuild
; (a test build - installed next to the real Lmonitor to check this installer - leaves the real
;  program, its "Start with Windows" task and RivaTuner profile alone)
[UninstallRun]
Filename: "{sys}\taskkill.exe"; Parameters: "/F /IM {#AppExe}"; Flags: runhidden; RunOnceId: "KillLmonitor"
; the "Start with Windows" task (if the user switched it on)
Filename: "{sys}\schtasks.exe"; Parameters: "/Delete /TN ""Lmonitor"" /F"; Flags: runhidden; RunOnceId: "LmonitorTask"
#endif

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
      SuppressibleMsgBox('The PawnIO sensor driver could not be installed (error ' + IntToStr(Code) + ').' + #13#10#13#10 +
                         'Lmonitor still works, but CPU temperature and power will show "--".' + #13#10 +
                         'Run this setup again later to try once more.',
                         mbError, MB_OK, IDOK);
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Dir: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
#ifndef TestBuild
    if RtssDir() <> '' then                       { the RivaTuner profile made at install }
      DeleteFile(RtssDir() + '\Profiles\{#AppExe}.cfg');
#endif
    Dir := ExpandConstant('{userappdata}\Lmonitor');
    { default = keep. A silent uninstall never deletes settings. }
    if (not UninstallSilent) and DirExists(Dir) then
      if MsgBox('Also delete your Lmonitor settings and game history?' + #13#10 +
                Dir + #13#10#13#10 + 'Choose No to keep them for a later install.',
                mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
        DelTree(Dir, True, True, True);
  end;
end;
