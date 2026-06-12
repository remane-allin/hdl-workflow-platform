param(
    [string]$WorkspaceRoot = ".",
    [string]$ProjectPath = "",
    [string]$RawInput = ""
)

. (Join-Path $PSScriptRoot "HdlHook.Common.ps1")

function Get-HdlHookPropertyValue {
    param(
        $Object,
        [Parameter(Mandatory = $true)][string]$Name
    )

    if ($null -eq $Object) {
        return $null
    }
    $property = $Object.PSObject.Properties[$Name]
    if ($null -eq $property) {
        return $null
    }
    return $property.Value
}

function Add-HdlHookTextFragment {
    param(
        $Value,
        [Parameter(Mandatory = $true)]$Fragments
    )

    if ($null -eq $Value) {
        return
    }
    if ($Value -is [string]) {
        if (-not [string]::IsNullOrWhiteSpace($Value)) {
            [void]$Fragments.Add($Value)
        }
        return
    }
    if ($Value -is [System.Collections.IDictionary]) {
        foreach ($item in $Value.Values) {
            Add-HdlHookTextFragment -Value $item -Fragments $Fragments
        }
        return
    }
    if ($Value -is [System.Collections.IEnumerable]) {
        foreach ($item in $Value) {
            Add-HdlHookTextFragment -Value $item -Fragments $Fragments
        }
        return
    }
    foreach ($property in $Value.PSObject.Properties) {
        Add-HdlHookTextFragment -Value $property.Value -Fragments $Fragments
    }
}

function Get-HdlHookCommandText {
    param(
        $Event,
        [string]$RawInput
    )

    $fragments = New-Object 'System.Collections.Generic.List[string]'
    Add-HdlHookTextFragment -Value (Get-HdlHookPropertyValue -Object $Event -Name "command") -Fragments $fragments

    foreach ($toolNameProperty in @("tool_name", "tool", "name", "recipient_name")) {
        Add-HdlHookTextFragment -Value (Get-HdlHookPropertyValue -Object $Event -Name $toolNameProperty) -Fragments $fragments
    }

    $toolInput = Get-HdlHookPropertyValue -Object $Event -Name "tool_input"
    Add-HdlHookTextFragment -Value (Get-HdlHookPropertyValue -Object $toolInput -Name "command") -Fragments $fragments
    Add-HdlHookTextFragment -Value $toolInput -Fragments $fragments

    if (($fragments.Count -eq 0) -and $RawInput) {
        Add-HdlHookTextFragment -Value $RawInput -Fragments $fragments
    }
    return ($fragments -join "`n")
}

function Test-HdlFrontdoorBaseline {
    param(
        [Parameter(Mandatory = $true)][string]$ProjectRoot
    )

    $manifestDir = Join-Path $ProjectRoot "work\memory\recovery\rollback_manifests"
    $specManifest = @(
        Get-ChildItem -Path $manifestDir -Filter "input_*.json" -ErrorAction SilentlyContinue
    )
    $docparseManifest = @(
        Get-ChildItem -Path $manifestDir -Filter "work_docparse_*.json" -ErrorAction SilentlyContinue
    )
    return (($specManifest.Count + $docparseManifest.Count) -gt 0)
}

function Test-HdlNodeBaseline {
    param(
        [Parameter(Mandatory = $true)][string]$ProjectRoot,
        [Parameter(Mandatory = $true)][string]$Node
    )

    $manifestDir = Join-Path $ProjectRoot "work\memory\recovery\rollback_manifests"
    $normalizedNode = $Node.Replace("\", "/")
    $nodeStem = $normalizedNode.Replace("/", "_")
    $nodeManifest = @(
        Get-ChildItem -Path $manifestDir -Filter "$nodeStem`_*.json" -ErrorAction SilentlyContinue
    )
    return ($nodeManifest.Count -gt 0)
}

function Test-HdlReportContains {
    param(
        [Parameter(Mandatory = $true)][string]$ProjectRoot,
        [Parameter(Mandatory = $true)][string]$RelPath,
        [Parameter(Mandatory = $true)][string]$Marker
    )

    $path = Join-Path $ProjectRoot $RelPath
    if (-not (Test-Path -LiteralPath $path)) {
        return $false
    }
    $text = Get-Content -LiteralPath $path -Raw -ErrorAction SilentlyContinue
    return $text.Contains($Marker)
}

function Test-HdlActiveChangeRequest {
    param(
        [Parameter(Mandatory = $true)][string]$ProjectRoot
    )

    $requestsDir = Join-Path $ProjectRoot "work/change\requests"
    $requests = @(Get-ChildItem -Path $requestsDir -Filter "CR-*.md" -ErrorAction SilentlyContinue)
    foreach ($request in $requests) {
        $text = (Get-Content -LiteralPath $request.FullName -Raw -ErrorAction SilentlyContinue).ToLowerInvariant()
        if ($text -match "(?m)^\s*-\s*status:\s*(open|impact_ready|approved)\b") {
            return $true
        }
    }
    return $false
}

function Get-HdlChangeIdFromRequest {
    param(
        [Parameter(Mandatory = $true)]$Request
    )

    $text = Get-Content -LiteralPath $Request.FullName -Raw -ErrorAction SilentlyContinue
    if ($text -match "(?m)^\s*-\s*id:\s*([A-Za-z0-9_-]+)\b") {
        return $Matches[1]
    }
    return $Request.BaseName
}

function Test-HdlChangeRecordsDescribeDelta {
    param(
        [Parameter(Mandatory = $true)][string]$ProjectRoot,
        [Parameter(Mandatory = $true)]$Request
    )

    $changeId = Get-HdlChangeIdFromRequest -Request $Request
    $impact = Join-Path $ProjectRoot "work/change\impact_analysis\$changeId.md"
    $approval = Join-Path $ProjectRoot "work/change\approvals\$changeId.md"
    if ((-not (Test-Path -LiteralPath $impact)) -or (-not (Test-Path -LiteralPath $approval))) {
        return $false
    }
    $impactText = Get-Content -LiteralPath $impact -Raw -ErrorAction SilentlyContinue
    foreach ($section in @("## Requirements", "## Artifacts", "## Required Verification")) {
        if (-not $impactText.Contains($section)) {
            return $false
        }
    }
    return ($impactText -match "(?m)^\s*-\s+\S")
}

function Get-HdlLatestCompleteApprovedChangeRequest {
    param(
        [Parameter(Mandatory = $true)][string]$ProjectRoot
    )

    $requestsDir = Join-Path $ProjectRoot "work/change\requests"
    $requests = @(Get-ChildItem -Path $requestsDir -Filter "CR-*.md" -ErrorAction SilentlyContinue)
    $approved = @()
    foreach ($request in $requests) {
        $text = (Get-Content -LiteralPath $request.FullName -Raw -ErrorAction SilentlyContinue).ToLowerInvariant()
        if (($text -match "(?m)^\s*-\s*status:\s*approved\b") -and
            (Test-HdlChangeRecordsDescribeDelta -ProjectRoot $ProjectRoot -Request $request)) {
            $approved += $request
        }
    }
    if ($approved.Count -eq 0) {
        return $null
    }
    return @($approved | Sort-Object LastWriteTimeUtc -Descending)[0]
}

function Test-HdlPostChangeFrontdoorGenerated {
    param(
        [Parameter(Mandatory = $true)][string]$ProjectRoot,
        [Parameter(Mandatory = $true)]$ApprovedRequest,
        [Parameter(Mandatory = $true)][string]$ScopeName,
        [string[]]$RequiredSections = @("verification_plan", "delivery_package")
    )

    $requestTime = $ApprovedRequest.LastWriteTimeUtc
    $frontdoorReport = Join-Path $ProjectRoot "output\reports\docparse\requirements_frontend_check.md"
    if (-not (Test-Path -LiteralPath $frontdoorReport)) {
        return "$ScopeName must reopen the requirements front door first; run requirements-frontdoor-check after the approved change before formal source edits"
    }
    $frontdoorItem = Get-Item -LiteralPath $frontdoorReport
    $frontdoorText = (Get-Content -LiteralPath $frontdoorReport -Raw -ErrorAction SilentlyContinue).ToLowerInvariant()
    if ($frontdoorText -notmatch "(?m)^\s*-?\s*result:\s*pass\b") {
        return "$ScopeName require requirements-frontdoor-check PASS before formal source edits"
    }
    if ($frontdoorItem.LastWriteTimeUtc -lt $requestTime) {
        return "$ScopeName require requirements-frontdoor-check to be rerun after the approved change before formal source edits"
    }

    $docsetManifest = Join-Path $ProjectRoot "output\docs\manifests\docset_manifest.json"
    $docPaths = @(
        (Join-Path $ProjectRoot "output\docs\application\application_guide.md"),
        (Join-Path $ProjectRoot "output\docs\design\microarchitecture_spec.md"),
        (Join-Path $ProjectRoot "output\docs\test\verification_plan.md"),
        (Join-Path $ProjectRoot "output\docs\delivery\delivery_package.md")
    )
    if ((-not (Test-Path -LiteralPath $docsetManifest)) -or (@($docPaths | Where-Object { -not (Test-Path -LiteralPath $_) }).Count -gt 0)) {
        return "$ScopeName require regenerating the docset with python -m hdlflow.cli generate-docs before formal source edits"
    }
    $docsetManifestItem = Get-Item -LiteralPath $docsetManifest
    $docItems = @($docPaths | ForEach-Object { Get-Item -LiteralPath $_ })
    if (($docsetManifestItem.LastWriteTimeUtc -lt $requestTime) -or (@($docItems | Where-Object { $_.LastWriteTimeUtc -lt $requestTime }).Count -gt 0)) {
        return "$ScopeName require generate-docs to be rerun after the approved change before formal source edits"
    }
    try {
        $manifest = Get-Content -LiteralPath $docsetManifest -Raw -ErrorAction Stop | ConvertFrom-Json
        $docs = @($manifest.documents | ForEach-Object { $_.doc_type })
        $missingDocs = @()
        foreach ($section in $RequiredSections) {
            if ($docs -notcontains $section) {
                $missingDocs += $section
            }
        }
        if ($missingDocs.Count -gt 0) {
            return "$ScopeName require generated document(s): $($missingDocs -join ', ')"
        }
    }
    catch {
        return "$ScopeName require a valid docset_manifest.json before formal source edits"
    }
    return ""
}

$event = Read-HdlHookJson -RawInput $RawInput
$command = Get-HdlHookCommandText -Event $event -RawInput $RawInput

if (Test-HdlCommandLooksDestructive -Command $command) {
    Write-HdlHookDecision -Decision block -Continue $false -Reason "destructive command requires explicit user request"
    exit 0
}

$normalizedParserCommand = $command.ToLowerInvariant().Replace("\", "/")
while ($normalizedParserCommand.Contains("//")) {
    $normalizedParserCommand = $normalizedParserCommand.Replace("//", "/")
}
if (($normalizedParserCommand -match "\bmineru-open-api\b.*\bflash-extract\b") -or
    ($normalizedParserCommand -match "\bflash-extract\b.*\bmineru-open-api\b") -or
    ($normalizedParserCommand -match "\bmineru-open-api\b.*(?:^|\s)--mode\s+flash\b")) {
    Write-HdlHookDecision -Decision block -Continue $false -Reason "DocParse formal evidence must use MinerU high-precision API (/api/v4/extract/task or /api/v4/file-urls/batch); flash extraction is forbidden"
    exit 0
}
$docparseRecordWritePattern = "apply_patch|set-content|add-content|out-file|new-item|remove-item|move-item|copy-item|\bni\b|\bdel\b|\brm\b|\bmkdir\b|>>|>\s*['""]?[^|]"
$illegalDocparseRecordPattern = "work/docparse/parsed/mineru_extract/(parse_operation_record|operation_record|analysis_record|process_violation_record|violation_record)\.md\b"
if (($normalizedParserCommand -match $docparseRecordWritePattern) -and
    ($normalizedParserCommand -match $illegalDocparseRecordPattern)) {
    Write-HdlHookDecision -Decision block -Continue $false -Reason "DocParse parsed evidence may contain parser outputs and provenance only; store operation notes under work/docparse/review or memory"
    exit 0
}
$manualRecordProvenanceMarker = "\b(operation_record|process_violation_record|violation_record|manual_review|docparse_operation_log)\b"
if (($normalizedParserCommand -match $docparseRecordWritePattern) -and
    ($normalizedParserCommand -match "work/docparse/parsed/mineru_extract/provenance\.ya?ml") -and
    ($normalizedParserCommand -match $manualRecordProvenanceMarker)) {
    Write-HdlHookDecision -Decision block -Continue $false -Reason "parser provenance must describe parser evidence only; do not link operation, violation, or manual review records from provenance.yaml"
    exit 0
}
$illegalAdHocArtifactPattern = "input/spec/(srs|acceptance_criteria|forbidden_designs|open_questions|requirements|module_plan|path_partition|decomposition_notes|design_blueprint)\.(ya?ml|json|md)|output/reports/design/reviewer_plan_review\.md"
if (($normalizedParserCommand -match $docparseRecordWritePattern) -and
    ($normalizedParserCommand -match $illegalAdHocArtifactPattern)) {
    Write-HdlHookDecision -Decision block -Continue $false -Reason "DocParse and design outputs must be produced from front-door YAML and platform generators; do not create sidecar operation, violation, review-plan, or design-blueprint files"
    exit 0
}
$designReportPattern = "output/docs"
if (($normalizedParserCommand -match $docparseRecordWritePattern) -and
    ($normalizedParserCommand -match $designReportPattern) -and
    ($normalizedParserCommand -notmatch "\b(generate-docs|generate-application-doc|generate-uarch-doc|generate-verification-doc|generate-delivery-doc)\b")) {
    Write-HdlHookDecision -Decision block -Continue $false -Reason "docset documents must be generated by python -m hdlflow.cli generate-docs after requirements-frontdoor-check passes"
    exit 0
}

$normalizedForProjectCreate = $command.ToLowerInvariant().Replace("\", "/")
while ($normalizedForProjectCreate.Contains("//")) {
    $normalizedForProjectCreate = $normalizedForProjectCreate.Replace("//", "/")
}
$officialProjectCreatePattern = "env/tool/scripts/(new-hdlproject\.ps1|new_hdl_project\.py)"
$directProjectCreatePattern = "hdlflow\.cli\s+init-project|\bhdlflow\s+init-project\b"
$manualProjectDirPattern = "\b(new-item|mkdir|copy-item|robocopy)\b.*\bprj/"
if (($normalizedForProjectCreate -notmatch $officialProjectCreatePattern) -and
    (($normalizedForProjectCreate -match $directProjectCreatePattern) -or
     ($normalizedForProjectCreate -match $manualProjectDirPattern))) {
    Write-HdlHookDecision -Decision block -Continue $false -Reason "project creation must use env/tool/scripts/New-HdlProject.ps1 or env/tool/scripts/new_hdl_project.py"
    exit 0
}
$controlledVivadoPattern = "env/tool/scripts/invoke-hdlvivado\.ps1\b|\binvoke-hdlvivado\.ps1\b"
$directVivadoPattern = "(^|[\s&;`"''])(vivado(\.bat|\.exe)?|[a-z]:/[^ \t\r\n`"'']*/vivado(\.bat|\.exe))[`"'']?\s+.*-mode\b"
if (($normalizedForProjectCreate -notmatch $controlledVivadoPattern) -and
    ($normalizedForProjectCreate -match $directVivadoPattern)) {
    Write-HdlHookDecision -Decision block -Continue $false -Reason "Vivado must be launched through env/tool/scripts/Invoke-HdlVivado.ps1 so journal and log files stay under output/fpga/vivado/logs"
    exit 0
}
$controlledVitisPattern = "env/tool/scripts/invoke-hdlvitis\.ps1\b|\binvoke-hdlvitis\.ps1\b|\bbuild-bootimage\.ps1\b"
$directVitisPattern = "(^|[\s&;`"''])(xsct(\.bat|\.exe)?|vitis(\.bat|\.exe)?|bootgen(\.bat|\.exe)?|[a-z]:/[^ \t\r\n`"'']*/xsct(\.bat|\.exe)|[a-z]:/[^ \t\r\n`"'']*/vitis(\.bat|\.exe)|[a-z]:/[^ \t\r\n`"'']*/bootgen(\.bat|\.exe))[`"'']?\s+"
if (($normalizedForProjectCreate -notmatch $controlledVitisPattern) -and
    ($normalizedForProjectCreate -match $directVitisPattern)) {
    Write-HdlHookDecision -Decision block -Continue $false -Reason "Vitis, XSCT, and bootgen must be launched through env/tool/scripts/Invoke-HdlVitis.ps1 or a generated Build-BootImage.ps1 wrapper after Loop3 preflight"
    exit 0
}

try {
    $projectRoot = Resolve-HdlProjectRoot -ProjectPath $ProjectPath -WorkspaceRoot $WorkspaceRoot
    $normalizedCommand = $command.ToLowerInvariant().Replace("\", "/")
    while ($normalizedCommand.Contains("//")) {
        $normalizedCommand = $normalizedCommand.Replace("//", "/")
    }
    $writePattern = "apply_patch|set-content|add-content|out-file|new-item|remove-item|move-item|copy-item|\bni\b|\bdel\b|\brm\b|\bmkdir\b|>>|>\s*['""]?[^|]|prototype-preflight|validate-prototype-plan|generate-xdc|generate-ps-pl-bd|generate-vitis-boot|loop1-refresh-reports|loop1-waveform-check|loop2-refresh-reports|loop2-build-bindings|loop2-database-preflight|invoke-hdlmodelsim\.ps1|invoke-hdlvivado\.ps1|invoke-hdlvitis\.ps1|build-bootimage\.ps1|\bxsct(\.bat|\.exe)?\b|\bvitis(\.bat|\.exe)?\b|\bbootgen(\.bat|\.exe)?\b|\bvsim\b|\bvlog\b"
    $sourceEditPattern = "apply_patch|set-content|add-content|out-file|new-item|remove-item|move-item|copy-item|\bni\b|\bdel\b|\brm\b|\bmkdir\b|>>|>\s*['""]?[^|]"
    $frontdoorPattern = "requirements-frontdoor-init|requirements-frontdoor-check|run-gate.*\b(spec|input|docparse|work/docparse|00|01)\b"
    $changeControlPattern = "change-open|change-impact|change-approve|change-close|change-check"
    $frontdoorGeneratorPattern = "generate-docs|generate-application-doc|generate-uarch-doc|generate-verification-doc|generate-delivery-doc|check-docset"
    $controlledFrontdoorPattern = "$frontdoorPattern|$changeControlPattern|$frontdoorGeneratorPattern"
    $controlledPrototypePattern = "prototype-preflight|validate-prototype-plan|generate-xdc|generate-ps-pl-bd|generate-vitis-boot|invoke-hdlvivado\.ps1|invoke-hdlvitis\.ps1|build-bootimage\.ps1"
    $legacySplitInputPattern = "input/(raw_" + "docs|require" + "ments)"
    if (($normalizedCommand -match $writePattern) -and
        ($normalizedCommand -match $legacySplitInputPattern)) {
        Write-HdlHookDecision -Decision block -Continue $false -Reason "new projects use the single front-door input root input/spec; split input roots are forbidden"
        exit 0
    }
    $frontdoorSourcePattern = "input/spec|work/docparse/frontdoor|work/docparse/structured_spec|work/docparse/req_decompose|work/docparse/architecture|work/docparse/verification|work/docparse/prototype|work/docparse/trace_matrix"
    $prototypeChangePattern = "work/loop3_fpga_proto/board_tests|work/loop3_fpga_proto/board_profiles|work/loop3_fpga_proto/scripts|output/fpga/vivado/constraints|output/fpga/vivado/scripts|output/fpga/vitis"
    $generatedFpgaOutputPattern = "output/fpga/vivado/constraints|output/fpga/vivado/scripts|output/fpga/vitis"
    $officialGeneratedFpgaPattern = "generate-xdc|generate-ps-pl-bd|generate-vitis-boot|invoke-hdlvivado\.ps1|invoke-hdlvitis\.ps1|build-bootimage\.ps1"
    $loop1FormalChangePattern = "output/rtl|output/tb|work/loop1_rtl_tb/sim"
    $loop2FormalChangePattern = "output/uvm|work/loop2_uvm/sim"
    $protectedGatePolicyPattern = "env/rule/global/gates|env/rule/project_default/project_config\.yaml|prj/.+/work/config/project_config\.yaml|env/core/hdlflow/gates\.py|env/core/hdlflow/frontdoor_guard\.py|env/core/hdlflow/ralph_loop\.py|env/core/hdlflow/requirements_frontend\.py|env/core/hdlflow/review\.py|env/core/hdlflow/waveform\.py|env/core/hooks/invoke-hdlpretoolguard\.ps1|env/tool/scripts/invoke-hdlloop3boardverify\.ps1|env/tool/scripts/invoke-hdlvitis\.ps1"
    $projectFrontdoorPopulateScriptPattern = "env/tool/scripts/populate_[a-z0-9_-]+_frontdoor\.py\b"
    $formalPattern = "output/rtl|output/tb|output/uvm|work/loop3_fpga_proto|output/fpga"
    if (($normalizedCommand -match $sourceEditPattern) -and
        ($normalizedCommand -match $protectedGatePolicyPattern)) {
        Write-HdlHookDecision -Decision block -Continue $false -Reason "AI agents cannot automatically modify gate policy or guard conditions to make a project pass; record suspected gate issues under review or memory and handle gate maintenance as a separate explicit platform task with regression evidence"
        exit 0
    }
    if (($normalizedCommand -match $sourceEditPattern) -and
        ($normalizedCommand -match "output/reports/loop1/rtl_skill_audit\.md") -and
        ($normalizedCommand -notmatch "rtl-skill-audit")) {
        Write-HdlHookDecision -Decision block -Continue $false -Reason "output/reports/loop1/rtl_skill_audit.md must be generated by python -m hdlflow.cli rtl-skill-audit --project <project>; do not hand-edit RTL skill audit evidence"
        exit 0
    }
    if (($normalizedCommand -match $writePattern) -and
        ($normalizedCommand -match $projectFrontdoorPopulateScriptPattern) -and
        (Test-HdlFrontdoorBaseline -ProjectRoot $projectRoot)) {
        Write-HdlHookDecision -Decision block -Continue $false -Reason "project requirement changes after a gate baseline must update the front-door source artifacts first; do not modify populate/front-door helper scripts to implement project-specific requirements"
        exit 0
    }
    if (($normalizedCommand -match $sourceEditPattern) -and
        ($normalizedCommand -match $generatedFpgaOutputPattern) -and
        ($normalizedCommand -notmatch $officialGeneratedFpgaPattern)) {
        Write-HdlHookDecision -Decision block -Continue $false -Reason "generated FPGA artifacts under output/fpga must be regenerated by the platform generators or tool wrappers; do not hand-edit generated XDC, BD Tcl, Vitis, boot, or bitstream artifacts"
        exit 0
    }
    if (($normalizedCommand -match $writePattern) -and
        (($normalizedCommand -match "invoke-hdlmodelsim\.ps1") -and ($normalizedCommand -match "\bloop1\b") -or
         ($normalizedCommand -match "loop1-refresh-reports|loop1-waveform-check"))) {
        if (-not (Test-HdlNodeBaseline -ProjectRoot $projectRoot -Node "work/docparse")) {
            Write-HdlHookDecision -Decision block -Continue $false -Reason "Loop1 tool entry requires a passed DocParse gate manifest first"
            exit 0
        }
    }
    if (($normalizedCommand -match $writePattern) -and
        (($normalizedCommand -match "invoke-hdlmodelsim\.ps1") -and ($normalizedCommand -match "\bloop2\b") -or
         ($normalizedCommand -match "loop2-refresh-reports|loop2-build-bindings|loop2-database-preflight"))) {
        if (-not (Test-HdlNodeBaseline -ProjectRoot $projectRoot -Node "work/docparse")) {
            Write-HdlHookDecision -Decision block -Continue $false -Reason "Loop2 tool entry requires a passed DocParse gate manifest first"
            exit 0
        }
        if (-not (Test-HdlNodeBaseline -ProjectRoot $projectRoot -Node "work/loop1_rtl_tb")) {
            Write-HdlHookDecision -Decision block -Continue $false -Reason "Loop2 tool entry requires a passed Loop1 gate manifest first"
            exit 0
        }
    }
    if (($normalizedCommand -match $writePattern) -and
        ($normalizedCommand -match "prototype-preflight|validate-prototype-plan|generate-xdc|generate-ps-pl-bd|generate-vitis-boot|invoke-hdlvivado\.ps1|invoke-hdlvitis\.ps1|build-bootimage\.ps1")) {
        if (-not (Test-HdlNodeBaseline -ProjectRoot $projectRoot -Node "work/docparse")) {
            Write-HdlHookDecision -Decision block -Continue $false -Reason "Loop3 tool entry requires a passed DocParse gate manifest first"
            exit 0
        }
        if (-not (Test-HdlNodeBaseline -ProjectRoot $projectRoot -Node "work/loop1_rtl_tb")) {
            Write-HdlHookDecision -Decision block -Continue $false -Reason "Loop3 tool entry requires a passed Loop1 gate manifest first"
            exit 0
        }
        if (-not (Test-HdlNodeBaseline -ProjectRoot $projectRoot -Node "work/loop2_uvm")) {
            Write-HdlHookDecision -Decision block -Continue $false -Reason "Loop3 tool entry requires a passed Loop2 gate manifest first"
            exit 0
        }
        if ($normalizedCommand -match "generate-xdc|generate-ps-pl-bd|generate-vitis-boot|invoke-hdlvivado\.ps1|invoke-hdlvitis\.ps1|build-bootimage\.ps1") {
            $databaseReady = Test-HdlReportContains -ProjectRoot $projectRoot -RelPath "output\reports\loop3\preflight\database_preflight.md" -Marker "result: PASS"
            $planReady = Test-HdlReportContains -ProjectRoot $projectRoot -RelPath "output\reports\loop3\preflight\prototype_plan_check.md" -Marker "- result: PASS"
            if ((-not $databaseReady) -or (-not $planReady)) {
                Write-HdlHookDecision -Decision block -Continue $false -Reason "Loop3 generation/tool entry requires prototype-preflight and validate-prototype-plan PASS reports first"
                exit 0
            }
        }
    }
    if (($normalizedCommand -match $writePattern) -and
        ($normalizedCommand -match $frontdoorSourcePattern) -and
        ($normalizedCommand -notmatch $controlledFrontdoorPattern) -and
        (Test-HdlFrontdoorBaseline -ProjectRoot $projectRoot) -and
        (-not (Test-HdlActiveChangeRequest -ProjectRoot $projectRoot))) {
        Write-HdlHookDecision -Decision block -Continue $false -Reason "front-door source changes after a gate baseline require change control first; run python -m hdlflow.cli change-open, then record impact/approval before rerunning requirements-frontdoor-check, generate-docs, and the DocParse gate"
        exit 0
    }
    if (($normalizedCommand -match $writePattern) -and
        ($normalizedCommand -match $prototypeChangePattern) -and
        ($normalizedCommand -notmatch $controlledPrototypePattern) -and
        (Test-HdlFrontdoorBaseline -ProjectRoot $projectRoot)) {
        $approvedRequest = Get-HdlLatestCompleteApprovedChangeRequest -ProjectRoot $projectRoot
        if ($null -eq $approvedRequest) {
            Write-HdlHookDecision -Decision block -Continue $false -Reason "prototype verification requirement changes after a gate baseline require a complete approved front-door change first; run python -m hdlflow.cli change-open, change-impact, and change-approve, and record changed requirements, artifacts, and verification before Loop3 or FPGA edits"
            exit 0
        }
        $postChangeReason = Test-HdlPostChangeFrontdoorGenerated -ProjectRoot $projectRoot -ApprovedRequest $approvedRequest -ScopeName "prototype verification changes" -RequiredSections @("verification_plan", "delivery_package")
        if (-not [string]::IsNullOrWhiteSpace($postChangeReason)) {
            Write-HdlHookDecision -Decision block -Continue $false -Reason $postChangeReason
            exit 0
        }
    }
    if (($normalizedCommand -match $sourceEditPattern) -and
        ($normalizedCommand -match $loop1FormalChangePattern) -and
        (Test-HdlNodeBaseline -ProjectRoot $projectRoot -Node "work/loop1_rtl_tb")) {
        $approvedRequest = Get-HdlLatestCompleteApprovedChangeRequest -ProjectRoot $projectRoot
        if ($null -eq $approvedRequest) {
            Write-HdlHookDecision -Decision block -Continue $false -Reason "Loop1 RTL/TB requirement changes after a work/loop1_rtl_tb gate baseline require a complete approved front-door change first; run python -m hdlflow.cli change-open, change-impact, and change-approve, and record changed requirements, artifacts, and verification before editing formal sources"
            exit 0
        }
        $postChangeReason = Test-HdlPostChangeFrontdoorGenerated -ProjectRoot $projectRoot -ApprovedRequest $approvedRequest -ScopeName "Loop1 RTL/TB requirement changes" -RequiredSections @("microarchitecture_specification", "verification_plan", "delivery_package")
        if (-not [string]::IsNullOrWhiteSpace($postChangeReason)) {
            Write-HdlHookDecision -Decision block -Continue $false -Reason $postChangeReason
            exit 0
        }
    }
    if (($normalizedCommand -match $sourceEditPattern) -and
        ($normalizedCommand -match $loop2FormalChangePattern) -and
        (Test-HdlNodeBaseline -ProjectRoot $projectRoot -Node "work/loop2_uvm")) {
        $approvedRequest = Get-HdlLatestCompleteApprovedChangeRequest -ProjectRoot $projectRoot
        if ($null -eq $approvedRequest) {
            Write-HdlHookDecision -Decision block -Continue $false -Reason "Loop2 UVM requirement changes after a work/loop2_uvm gate baseline require a complete approved front-door change first; run python -m hdlflow.cli change-open, change-impact, and change-approve, and record changed requirements, artifacts, and verification before editing formal sources"
            exit 0
        }
        $postChangeReason = Test-HdlPostChangeFrontdoorGenerated -ProjectRoot $projectRoot -ApprovedRequest $approvedRequest -ScopeName "Loop2 UVM requirement changes" -RequiredSections @("verification_plan", "delivery_package")
        if (-not [string]::IsNullOrWhiteSpace($postChangeReason)) {
            Write-HdlHookDecision -Decision block -Continue $false -Reason $postChangeReason
            exit 0
        }
    }
    $agentRole = ""
    if ($env:HDLFLOW_AGENT_ROLE) {
        $agentRole = $env:HDLFLOW_AGENT_ROLE.ToLowerInvariant().Replace("-", "_").Replace(" ", "_")
        switch ($agentRole) {
            "spec_agent" { $agentRole = "spec" }
            "arch_agent" { $agentRole = "arch" }
            "exec_agent" { $agentRole = "exec" }
            "sim_agent" { $agentRole = "sim" }
            "review_agent" { $agentRole = "review" }
            "arbtr_agent" { $agentRole = "arbtr" }
            "arbitration" { $agentRole = "arbtr" }
        }
    }
    $agentWritePrefixes = @{
        spec = @("input/spec", "work/docparse/frontdoor", "work/docparse/structured_spec", "work/docparse/req_decompose", "work/docparse/trace_matrix")
        arch = @("work/docparse/architecture")
        exec = @("output/rtl", "output/tb")
        sim = @("output/uvm", "output/reports/loop1", "output/reports/loop2", "output/reports/loop3", "work/loop1_rtl_tb/_runtime", "work/loop1_rtl_tb/sim", "work/loop2_uvm/_runtime", "work/loop2_uvm/sim", "work/loop3_fpga_proto/_runtime")
        review = @("work/docparse/review", "output/reports/review")
        arbtr = @("work/memory/", "work/gates/", "output/reports/gates", "output/reports/freeze")
    }
    $controlledPrefixes = @()
    foreach ($key in $agentWritePrefixes.Keys) {
        $controlledPrefixes += $agentWritePrefixes[$key]
    }
    if (($normalizedCommand -match $writePattern) -and $agentRole -and $agentWritePrefixes.ContainsKey($agentRole)) {
        $hits = @($controlledPrefixes | Where-Object { $normalizedCommand.Contains($_) })
        if ($hits.Count -gt 0) {
            $allowed = @($agentWritePrefixes[$agentRole])
            $blocked = @()
            foreach ($hit in $hits) {
                $isAllowed = $false
                foreach ($prefix in $allowed) {
                    if (($hit -eq $prefix) -or $hit.StartsWith("$prefix/")) {
                        $isAllowed = $true
                        break
                    }
                }
                if (-not $isAllowed) {
                    $blocked += $hit
                }
            }
            if ($blocked.Count -gt 0) {
                Write-HdlHookDecision -Decision block -Continue $false -Reason "agent role $agentRole cannot write: $($blocked -join ', '); allowed write roots: $($allowed -join ', ')"
                exit 0
            }
        }
    }
    if (($normalizedCommand -match $writePattern) -and
        ($normalizedCommand -match $formalPattern) -and
        ($normalizedCommand -notmatch $frontdoorPattern)) {
        $manifestDir = Join-Path $projectRoot "work\memory\recovery\rollback_manifests"
        $docparseManifest = @(
            Get-ChildItem -Path $manifestDir -Filter "work_docparse_*.json" -ErrorAction SilentlyContinue
        )
        if ($docparseManifest.Count -eq 0) {
            Write-HdlHookDecision -Decision block -Continue $false -Reason "formal implementation artifacts require a passed DocParse gate manifest first; run requirements-frontdoor-check and the DocParse gate before writing output/rtl, output/tb, output/uvm, work/loop3_fpga_proto, or output/fpga"
            exit 0
        }
    }
}
catch {
    if ($command) {
        $normalizedCommand = $command.ToLowerInvariant().Replace("\", "/")
        if (($normalizedCommand -match "set-content|add-content|out-file|new-item|remove-item|move-item|copy-item|apply_patch|>>|>") -and
            ($normalizedCommand -match "output/rtl|output/tb|output/uvm|work/loop3_fpga_proto|output/fpga")) {
            Write-HdlHookDecision -Decision block -Continue $false -Reason "formal implementation artifact write could not be matched to a reviewed project; set HDL_PROJECT_PATH or pass ProjectPath after requirements review"
            exit 0
        }
    }
    # If project inference is unavailable and no formal output write is visible,
    # keep this hook permissive.
}

Write-HdlHookDecision -Decision approve -Reason "HDL workflow guard passed"
