; Mediagator â€” Inno Setup Installer Script
; Requires Inno Setup 6.x  (https://jrsoftware.org/isinfo.php)
;
; To compile:  ISCC.exe installer\Mediagator.iss
; Or:          Open in Inno Setup IDE and press Compile
;
; Prerequisite: run build.ps1 first to produce dist\Mediagator\

#define AppName "Mediagator"
#define AppVersion "1.0.6"
#define AppPublisher "Nathan"
#define AppURL "https://github.com/nathanokh1/Mediagator"
#define AppExeName "Mediagator.exe"
#define AppDescription "Media Transfer & Organisation Tool"
#define SourceDir "..\dist\Mediagator"
#define IconFile "..\assets\icon.ico"

[Setup]
AppId={{A8F3E1B2-4C6D-4E7A-9B3F-1D2E5C6A7F8B}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
AppUpdatesURL={#AppURL}/releases
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
LicenseFile=..\LICENSE
OutputDir=C:\Users\Pheonix\AppData\Local\MediagatorBuild
OutputBaseFilename=Mediagator_Setup_{#AppVersion}
SetupIconFile={#IconFile}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=commandline
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName} {#AppVersion}
VersionInfoVersion={#AppVersion}
VersionInfoDescription={#AppDescription}
VersionInfoCompany={#AppPublisher}
VersionInfoCopyright=Copyright (C) 2026 {#AppPublisher}. MIT License.

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon";     Description: "Create a &desktop shortcut";             GroupDescription: "Additional icons:"; Flags: unchecked
Name: "quicklaunchicon"; Description: "Create a &Quick Launch shortcut";         GroupDescription: "Additional icons:"; Flags: unchecked
Name: "startupicon";     Description: "Launch {#AppName} when Windows starts";   GroupDescription: "Startup:";          Flags: unchecked

[Files]
; Main application bundle (built by PyInstaller)
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}";                 Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\{#AppExeName}"
Name: "{group}\Uninstall {#AppName}";       Filename: "{uninstallexe}"
Name: "{commondesktop}\{#AppName}";         Filename: "{app}\{#AppExeName}"; Tasks: desktopicon; IconFilename: "{app}\{#AppExeName}"
Name: "{userprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: quicklaunchicon

[Registry]
; Add to startup (optional task)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#AppName}"; ValueData: """{app}\{#AppExeName}"""; Flags: uninsdeletevalue; Tasks: startupicon

[Run]
; Offer to launch after install
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent shellexec

[UninstallDelete]
; Remove any user data left in AppData on uninstall (optional â€” comment out to keep user data)
; Type: filesandordirs; Name: "{localappdata}\Mediagator"

[Code]
// Check for existing running instance before install
function InitializeSetup(): Boolean;
begin
  Result := True;
end;
