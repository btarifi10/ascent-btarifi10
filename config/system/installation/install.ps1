# ensure current directory is root of pipeline
$title    = 'Current Directory'
$question = 'Have you navigated to the root of the ASCENT repository?'
$choices  = '&Yes', '&No'
$decision = $Host.UI.PromptForChoice($title, $question, $choices, 1)
if ($decision -eq 0) {
    Write-Host 'Great, proceeding with installation.'

    # package installation
    conda create --name ascent -y
    conda activate ascent
    conda uninstall -y python
    conda install -y python=3.7
    python C:\Users\jec91\Miniconda3\envs\ascent\Lib\site-packages\pip install --upgrade pip setuptools wheel
    python C:\Users\jec91\Miniconda3\envs\ascent\Lib\site-packages\pip install pillow>=5.2.0 numpy>=1.16.4 shapely>=1.6.4 matplotlib>=3.2.1 pyclipper>=1.1.0 pygame>=1.9.6 pymunk>=5.5.0 scipy>=1.1.0 pandas>=0.25.1 openpyxl>=3.0.3 opencv-python quantiphy
    
    # shortcut creation
    $title    = 'ASCENT Conda Environment'
    $question = 'Do you want to save a shortcut for the "ascent" Conda environment to your Desktop?'
    $choices  = '&Yes', '&No'
    $decision = $Host.UI.PromptForChoice($title, $question, $choices, 1)
    if ($decision -eq 0) {
        $Arguments = "-ExecutionPolicy ByPass -NoExit -Command `"& `'C:\Users\" + $env:UserName + "\Miniconda3\shell\condabin\conda-hook.ps1`' ; conda activate ascent; cd `'" + (Get-Item .).FullName + "`'"
        $TargetFile = '%windir%\System32\WindowsPowerShell\v1.0\powershell.exe'
        $ShortcutFile = 'Desktop\ASCENT.lnk'
        $WScriptShell = New-Object -ComObject WScript.Shell
        $Shortcut = $WScriptShell.CreateShortcut($ShortcutFile)
        $Shortcut.TargetPath = $TargetFile
        $Shortcut.Arguments = $Arguments
        $Shortcut.Save()
        
        Write-Host 'Saved shortcut to ' + $ShortcutFile

    } else {
        Write-Host 'Did not save shortcut.'
    }
} else {
    Write-Host 'Please do so and re-run.'
}


