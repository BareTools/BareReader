; BareReader Installer Script (fixed)

Name "BareReader"
OutFile "BareReaderInstaller.exe"
InstallDir "$PROGRAMFILES\BareReader"
RequestExecutionLevel admin
SetCompress auto
SetCompressor lzma

!include "FileFunc.nsh"
!include "LogicLib.nsh"

Section "Install"

    SetOutPath "$INSTDIR"
    File "barereader.exe"

    ; Create Desktop Shortcut
    CreateShortcut "$DESKTOP\\BareReader.lnk" "$INSTDIR\\barereader.exe"

    ; Add to Open With for .pdf
    WriteRegStr HKCR "Applications\\barereader.exe\\shell\\open\\command" "" '"$INSTDIR\\barereader.exe" "%1"'
    WriteRegStr HKCR ".pdf\\OpenWithProgids" "barereader.exe" ""

SectionEnd

Section "Uninstall"

    Delete "$INSTDIR\\barereader.exe"
    Delete "$DESKTOP\\BareReader.lnk"
    RMDir "$INSTDIR"

    DeleteRegKey HKCR "Applications\\barereader.exe"
    DeleteRegValue HKCR ".pdf\\OpenWithProgids" "barereader.exe"

SectionEnd