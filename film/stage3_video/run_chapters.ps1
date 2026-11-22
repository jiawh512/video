# 逐章批量重制：一次跑完第一、二、三章（顺序执行，每章跑完自动接下一章）
$ErrorActionPreference = 'Continue'
$ws = 'D:\Backup\Documents\deepseek-harness\default-workspace'
$log = Join-Path $ws 'chapter-queue.log'
function Note($t) { "$(Get-Date -Format 'MM-dd HH:mm:ss')  $t" | Out-File -FilePath $log -Append -Encoding utf8 }

$chapters = @(
    @{ n = 1;  story = 'E:\神秘复苏_自动化生成工具_Desktop版\third_party\novel-to-script-team\outputs\神秘复苏\第一章_v2\分镜表.json'; out = 'E:\神秘复苏_视觉资产\32_第一章_重制' },
    @{ n = 2;  story = 'E:\神秘复苏_自动化生成工具_Desktop版\third_party\novel-to-script-team\outputs\神秘复苏\第二章\分镜表.json';    out = 'E:\神秘复苏_视觉资产\33_第二章_重制' },
    @{ n = 3;  story = 'E:\神秘复苏_自动化生成工具_Desktop版\third_party\novel-to-script-team\outputs\神秘复苏\第三章\分镜表.json';    out = 'E:\神秘复苏_视觉资产\34_第三章_重制2' },
    @{ n = 5;  story = 'E:\神秘复苏_自动化生成工具_Desktop版\third_party\novel-to-script-team\outputs\神秘复苏\第5章\分镜表.json';   out = 'E:\神秘复苏_视觉资产\36_第五章' },
    @{ n = 6;  story = 'E:\神秘复苏_自动化生成工具_Desktop版\third_party\novel-to-script-team\outputs\神秘复苏\第6章\分镜表.json';   out = 'E:\神秘复苏_视觉资产\37_第六章' },
    @{ n = 7;  story = 'E:\神秘复苏_自动化生成工具_Desktop版\third_party\novel-to-script-team\outputs\神秘复苏\第7章\分镜表.json';   out = 'E:\神秘复苏_视觉资产\38_第七章' },
    @{ n = 8;  story = 'E:\神秘复苏_自动化生成工具_Desktop版\third_party\novel-to-script-team\outputs\神秘复苏\第8章\分镜表.json';   out = 'E:\神秘复苏_视觉资产\39_第八章' },
    @{ n = 9;  story = 'E:\神秘复苏_自动化生成工具_Desktop版\third_party\novel-to-script-team\outputs\神秘复苏\第9章\分镜表.json';   out = 'E:\神秘复苏_视觉资产\40_第九章' },
    @{ n = 10; story = 'E:\神秘复苏_自动化生成工具_Desktop版\third_party\novel-to-script-team\outputs\神秘复苏\第10章\分镜表.json';  out = 'E:\神秘复苏_视觉资产\41_第十章' }
)

$py = 'E:\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI\.venv\Scripts\python.exe'
$comfyWd = 'E:\Comfy-Desktop\ComfyUI-Installs\ComfyUI'
$yaml = "$env:APPDATA\Comfy Desktop\instance-model-paths\inst-1787846834959.yaml"
$wd = 'E:\神秘复苏_自动化生成工具_Desktop版\神秘复苏_自动化生成工具\t2v_wan21'

function Ensure-ComfyUI {
    if (Test-NetConnection -ComputerName 127.0.0.1 -Port 8188 -InformationLevel Quiet -WarningAction SilentlyContinue) { return $true }
    Note 'ComfyUI 未运行，拉起'
    $argStr = '-s ComfyUI\main.py --feature-flag show_signin_button=true --feature-flag enable_telemetry=true --enable-manager --extra-model-paths-config "' + $yaml + '" --input-directory "E:\Comfy-Desktop\ComfyUI-Shared\input" --output-directory "E:\Comfy-Desktop\ComfyUI-Shared\output" --port 8188'
    Start-Process -FilePath $py -ArgumentList $argStr -WorkingDirectory $comfyWd -WindowStyle Hidden -RedirectStandardOutput 'E:\Comfy-Desktop\comfyui-headless.log' -RedirectStandardError 'E:\Comfy-Desktop\comfyui-headless.err.log'
    for ($i = 0; $i -lt 40; $i++) {
        Start-Sleep -Seconds 4
        if (Test-NetConnection -ComputerName 127.0.0.1 -Port 8188 -InformationLevel Quiet -WarningAction SilentlyContinue) { return $true }
    }
    return $false
}

& nvidia-smi -pl 450 2>$null | Out-Null
Note '=== 批量重制开始（第 1/2/3 章）==='

foreach ($c in $chapters) {
    if (-not (Ensure-ComfyUI)) { Note "第 $($c.n) 章：ComfyUI 起不来，跳过"; continue }
    New-Item -ItemType Directory -Force -Path $c.out | Out-Null
    $final = Join-Path $c.out ("神秘复苏_第{0}章_成片.mp4" -f $c.n)
    if (Test-Path $final) { Note "第 $($c.n) 章已完成，跳过"; continue }

    Note "第 $($c.n) 章：开始渲染 -> $($c.out)"
    @{ chapter = $c.n; story_json = $c.story; out_dir = $c.out } | ConvertTo-Json | Set-Content (Join-Path $ws 'current_chapter.json') -Encoding UTF8

    $env:PYTHONIOENCODING = 'utf-8'
    $env:STORY_JSON = $c.story
    $env:OUT_DIR = $c.out
    $p = Start-Process -FilePath 'python' -ArgumentList '-u', 'run_storyboard_test.py', 'all' -WorkingDirectory $wd -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $c.out 'run.log') -RedirectStandardError (Join-Path $c.out 'run.err.log')
    $p.WaitForExit()

    $big = Get-ChildItem $c.out -Filter '分层试跑_*.mp4' -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($big) {
        Move-Item $big.FullName $final -Force
        Note "第 $($c.n) 章：完成 -> $final"
    } else {
        Note "第 $($c.n) 章：没有产出成片（看 $($c.out)\run.log）"
    }
}

Note '=== 批量重制结束 ==='

