# Graph Report - mainproject  (2026-09-18)

## Corpus Check
- 198 files · ~368,194 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 263 file(s) not represented in the graph (top: .bsv 164, .tcl 54, (none) 11)

## Summary
- 919 nodes · 1080 edges · 96 communities (66 shown, 30 thin omitted)
- Extraction: 83% EXTRACTED · 17% INFERRED · 0% AMBIGUOUS · INFERRED: 184 edges (avg confidence: 0.84)
- Token cost: 2,376,041 input · 0 output

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 7
- Community 8
- Community 9
- Community 10
- Community 11
- Community 12
- Community 13
- Community 14
- Community 15
- Community 16
- Community 17
- Community 18
- Community 19
- Community 20
- Community 21
- Community 22
- Community 23
- Community 24
- Community 25
- Community 26
- Community 27
- Community 28
- Community 29
- Community 30
- Community 31
- Community 32
- Community 33
- Community 34
- Community 35
- Community 36
- Community 37
- Community 38
- Community 39
- Community 40
- Community 41
- Community 42
- Community 43
- Community 44
- Community 45
- Community 46
- Community 47
- Community 48
- Community 49
- Community 50
- Community 51
- Community 52
- Community 53
- Community 54
- Community 55
- Community 56
- Community 57
- Community 58
- Community 59
- Community 60
- Community 61
- Community 62
- Community 63
- Community 64
- Community 65
- Community 66
- Community 67
- Community 68
- Community 69
- Community 70
- Community 71
- Community 72
- Community 73
- Community 74
- Community 75
- Community 76
- Community 77
- Community 78
- Community 79
- Community 80
- Community 81
- Community 82
- Community 83
- Community 84
- Community 85
- Community 86
- Community 87
- Community 88
- Community 89
- Community 90
- Community 91
- Community 92
- Community 93
- Community 95

## God Nodes (most connected - your core abstractions)
1. `Seminar: Verification Methodologies for RISC-V Processors` - 13 edges
2. `PATARA self-testing test generator` - 12 edges
3. `REVERSI (modify, restore, compare)` - 11 edges
4. `h64 core64.yaml (hypervisor-capable core config)` - 10 edges
5. `Slide-by-Slide Content (18-slide deck)` - 10 edges
6. `PATARA: A Self-Testing Framework for RISC-V + Co-processor (Gesper et al., 2026) - base paper` - 10 edges
7. `ClassDiagram` - 9 edges
8. `c32/rv64i_isa.yaml (RV32IMSU CSR ISA spec)` - 9 edges
9. `c32_imacsu/core32.yaml (IMACSU core build config)` - 9 edges
10. `c32_imacsu/rv32i_isa.yaml (RV32IMACSU CSR ISA spec)` - 9 edges

## Surprising Connections (you probably didn't know these)
- `Seminar Abstract (converted docx)` --conceptually_related_to--> `Seminar Abstract PDF`  [INFERRED]
  graphify-out/converted/Kevin Jose Seminar_Abstract_c93315e2.md → seminar/seminarppt/Kevin Jose Seminar_Abstract.pdf
- `Hardware implementation of various 32-bit and 64-bit multipliers using Bluespec (Report.pdf)` --conceptually_related_to--> `h64 m_extension (mul_stages_in/out 1, div 32)`  [INFERRED]
  c-class/src/obsolete/m_ext/multiplier_designs/Report.pdf → c-class/sample_config/h64/core64.yaml
- `Seminar Abstract (converted docx)` --conceptually_related_to--> `Five verification technique families`  [INFERRED]
  graphify-out/converted/Kevin Jose Seminar_Abstract_c93315e2.md → seminar/02-GUIDE-APPROVAL-BRIEF.md
- `Seminar Papers Summary table (converted docx)` --cites--> `chiRVFormal: Formal Verification of RISC-V Processor Chisel Designs (Shen et al., 2026)`  [EXTRACTED]
  graphify-out/converted/Kevin Jose Seminar_Papers_Summary_831e1309.md → seminar/seminarppt/papers/𝜒RVFormal Formal verification of RISC-V processor Chisel designs.pdf
- `Seminar Papers Summary table (converted docx)` --cites--> `Base paper: A Self-Testing Framework for a RISC-V-Based System with a Co-processor (Gesper et al., 2026)`  [EXTRACTED]
  graphify-out/converted/Kevin Jose Seminar_Papers_Summary_831e1309.md → seminar/seminarppt/papers/A Self-Testing Framework for Verification and Validation of.pdf

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **SHAKTI repositories pinned for c64 build** — c_class_test_soc_c64_c32_c64_deps_caches_mmu, c_class_test_soc_c64_c32_c64_deps_csrbox, c_class_test_soc_c64_c32_c64_deps_riscv_config, c_class_test_soc_c64_c32_c64_deps_devices, c_class_test_soc_c64_c32_c64_deps_verification [EXTRACTED 1.00]
- **C-Class in-order pipeline stages** — c_class_docs_source_pipeline_instrfetch, c_class_docs_source_pipeline_decode, c_class_docs_source_pipeline_execution, c_class_docs_source_pipeline_memaccess, c_class_docs_source_pipeline_writeback [EXTRACTED 1.00]
- **C-Class memory subsystem (caches, TLBs, PTWALK, bus)** — c_class_docs_source_pipeline_icache_itlb, c_class_docs_source_pipeline_dcache_dtlb, c_class_docs_source_pipeline_ptwalk, c_class_docs_source_pipeline_busfabric [EXTRACTED 1.00]
- **chiRVFormal verification flow** — seminar__qa_slide_05_high_level_chisel_reference_model, seminar__qa_slide_05_statecheck_actioncheck_sync, seminar__qa_slide_05_pono_smtbmc_boolector [EXTRACTED 1.00]
- **INSTILLER methodology components** — seminar__qa_slide_07_coverage_guided_fuzzing, seminar__qa_slide_07_vaco, seminar__qa_slide_07_interrupt_exception_injection, seminar__qa_slide_07_hw_aware_seed_mutation [EXTRACTED 1.00]
- **Bluespec multiplier algorithm families compared in Report.pdf** — c_class_src_obsolete_m_ext_multiplier_designs_report_shift_and_add_multiplier, c_class_src_obsolete_m_ext_multiplier_designs_report_booth_multiplier, c_class_src_obsolete_m_ext_multiplier_designs_report_radix2_multiplier, c_class_src_obsolete_m_ext_multiplier_designs_report_radix4_multiplier, c_class_src_obsolete_m_ext_multiplier_designs_report_wallace_tree_multiplier [EXTRACTED 1.00]
- **PATARA extensions that patch REVERSI blind spots** — seminar_01_patara_full_explainer_interleaving, seminar_01_patara_full_explainer_operand_swapping, seminar_01_patara_full_explainer_hazard_sequence_generation, seminar_01_patara_full_explainer_cache_miss_generation, seminar_01_patara_full_explainer_twin_based_coprocessor_verification [EXTRACTED 1.00]
- **PATARA incremental configurations raising condition coverage** — seminar__qa_slide_14_instruction_combinations, seminar__qa_slide_14_operand_switching, seminar__qa_slide_14_interleaving, seminar__qa_slide_14_hazard_sequences, seminar__qa_slide_14_cache_tests [EXTRACTED 1.00]
- **PATARA main contributions pipeline** — seminar__qa_slide_10_patara, seminar__qa_slide_10_reversi_self_tests, seminar__qa_slide_10_hazard_cache_gen, seminar__qa_slide_10_twin_coproc_verification [EXTRACTED 1.00]
- **Processor verification approaches compared on slide 16** — seminar_qa2_s16_xrvformal, seminar_qa2_s16_vector_accelerator, seminar_qa2_s16_instiller, seminar_qa2_s16_pfv, seminar_qa2_s16_patara [EXTRACTED 1.00]
- **REVERSI modify-restore-compare flow** — seminar__qa_slide_12_modification_step, seminar__qa_slide_12_restoring_step, seminar__qa_slide_12_comparison_step [EXTRACTED 1.00]
- **Surveyed RISC-V verification approaches** — seminar_qa_slide_17_formal_methods, seminar_qa_slide_17_uvm_cosimulation, seminar_qa_slide_17_instiller_fuzzing, seminar_qa_slide_17_patara [EXTRACTED 1.00]
- **Modify, restore, compare register check sequence** — s11_modification_operation, s11_restoring_operation, s11_compare_focus_target [EXTRACTED 1.00]
- **Real bugs PATARA found in the pipeline** — s16_forwarding_multicycle_divide, s16_cache_miss_during_multiply, s16_load_jalr_forwarding, s16_cache_miss_stall_combinations [EXTRACTED 1.00]
- **Surveyed RISC-V verification papers (roles: Survey)** — s4_xrvformal, s4_riscv_vector_accelerator_functional_verification, s4_instiller, s4_polynomial_formal_verification_riscv [EXTRACTED 1.00]
- **Seminar agenda sections (1-7)** — seminar__qa_slide_02_introduction_objective, seminar__qa_slide_02_literature_survey_supporting_papers, seminar__qa_slide_02_literature_survey_base_paper, seminar__qa_slide_02_applications_relevance, seminar__qa_slide_02_comparison_alternate_approaches, seminar__qa_slide_02_conclusion, seminar__qa_slide_02_references [EXTRACTED 1.00]
- **Five papers covering distinct RISC-V verification technique families** — seminar_seminarppt_papers_a_self_testing_framework_for_verification_and_validation_of, seminar_seminarppt_papers_functional_verification_of_a_risc_v_vector_accelerator, seminar_seminarppt_papers_instiller_toward_efficient_and_realistic_rtl_fuzzing, seminar_seminarppt_papers_polynomial_formal_verification_of_a_risc_v_processor, seminar_seminarppt_papers__rvformal_formal_verification_of_risc_v_processor_chisel_designs [EXTRACTED 1.00]
- **Five surveyed RISC-V verification papers (four supporting plus base paper)** — seminar_qa2_grid_xrvformal, seminar_qa2_grid_vector_accelerator_verification, seminar_qa2_grid_instiller, seminar_qa2_grid_polynomial_formal_verification, seminar_qa2_grid_patara [EXTRACTED 1.00]
- **Literature survey: four supporting papers plus PATARA base paper** — seminar__qa_slide_04_xrvformal, seminar__qa_slide_04_riscv_vector_accelerator, seminar__qa_slide_04_instiller, seminar__qa_slide_04_polynomial_formal_verification, seminar__qa_slide_04_patara [EXTRACTED 1.00]
- **PATARA extensions patching coverage blind spots** — seminar_qa2_grid_operand_swapping, seminar_qa2_grid_hazard_sequence_generation, seminar_qa2_grid_cache_miss_generation, seminar_qa2_grid_twin_coprocessor_verification [EXTRACTED 1.00]
- **PATARA framework and its four extensions** — seminar__qa_grid_a_xml_flow, seminar__qa_grid_a_hazard_sequences, seminar__qa_grid_a_operand_swapping, seminar__qa_grid_a_cache_miss_generation, seminar__qa_grid_a_twin_based_coprocessor_verification [EXTRACTED 1.00]
- **PATARA incremental generation configurations** — seminar_qa2_s14_instruction_combinations, seminar_qa2_s14_operand_switching, seminar_qa2_s14_interleaving, seminar_qa2_s14_hazard_sequences, seminar_qa2_s14_cache_tests [EXTRACTED 1.00]
- **Verification approaches compared against PATARA** — seminar_qa3_s16_xrvformal, seminar_qa3_s16_vector_accelerator, seminar_qa3_s16_instiller, seminar_qa3_s16_pfv, seminar_qa3_s16_patara [EXTRACTED 1.00]
- **Compared RISC-V verification approaches** — seminar__qa_slide_16_xrvformal, seminar__qa_slide_16_vector_accel, seminar__qa_slide_16_instiller, seminar__qa_slide_16_pfv, seminar__qa_slide_16_patara [EXTRACTED 1.00]
- **Base paper ALFF pipeline (clinical, preprocessing, FFT, z-score)** — seminar_ref_diya_clinical_scales, seminar_ref_diya_fmri_preprocessing, seminar_ref_diya_fft, seminar_ref_diya_alff, seminar_ref_diya_zscore_standardization [EXTRACTED 1.00]
- **Five-modality PD literature survey (EEG, MEG, fNIRS, source EEG, fMRI)** — seminar_ref_diya_paper1_eeg_network_early_pd, seminar_ref_diya_paper2_meg_progression, seminar_ref_diya_paper3_fnirs_monitoring, seminar_ref_diya_paper4_eeg_source_networks, seminar_ref_diya_base_paper_alff [EXTRACTED 1.00]
- **Literature survey papers I-V** — seminar_ref_final1_paper1_iot_ml_crop_recommendation, seminar_ref_final1_paper2_ml_xai_crop_recommendation, seminar_ref_final1_paper3_xai_crop, seminar_ref_final1_paper4_ai_smart_crop_recommendation, seminar_ref_final1_paper5_integrated_smart_agriculture [EXTRACTED 1.00]
- **Literature survey papers (review papers 1-4 and base paper)** — seminar_ref_john_sander_2021, seminar_ref_john_karthikeyan_2026, seminar_ref_john_patil_2023, seminar_ref_john_ye_2024, seminar_ref_john_chen_2023 [EXTRACTED 1.00]
- **U-Net-CSP pipeline (ROI, preprocessing, network, loss, 3-D reconstruction)** — seminar_ref_john_roi_detection, seminar_ref_john_preprocessing, seminar_ref_john_unet_csp, seminar_ref_john_combined_loss, seminar_ref_john_3d_reconstruction [EXTRACTED 1.00]
- **Verification method trade-off axes** — seminar__qa_slide_03_core_challenge_no_golden_answer, seminar__qa_slide_03_test_source_tradeoff, seminar__qa_slide_03_correctness_oracle_tradeoff [EXTRACTED 1.00]
- **UVM verification flow of the RISC-V vector accelerator** — seminar__qa_slide_06_uvm_testbench, seminar__qa_slide_06_spike_iss_golden_model, seminar__qa_slide_06_sva_assertions, seminar__qa_slide_06_riscv_dv_jenkins_ci [EXTRACTED 1.00]
- **Four supporting papers surveyed against the PATARA base paper** — seminar__qa_grid_a_xrvformal, seminar__qa_grid_a_vector_accelerator_verification, seminar__qa_grid_a_instiller, seminar__qa_grid_a_polynomial_formal_verification, seminar__qa_grid_a_patara [EXTRACTED 1.00]
- **Four extensions patching blind spots of the XML flow** — seminar_qa_slide_13_operand_swapping, seminar_qa_slide_13_hazard_sequences, seminar_qa_slide_13_cache_miss_gen, seminar_qa_slide_13_twin_coprocessor_verification [EXTRACTED 1.00]
- **Polynomial formal verification methodology (BDDs, instruction isolation, FSM walk)** — seminar__qa_slide_08_binary_decision_diagrams, seminar__qa_slide_08_single_instruction_isolation, seminar__qa_slide_08_control_unit_fsm_walk [EXTRACTED 1.00]
- **Supporting papers relying on reference model or exhaustive proof** — seminar__qa_slide_09_xrvformal, seminar__qa_slide_09_vector_accel, seminar__qa_slide_09_instiller, seminar__qa_slide_09_pfv [EXTRACTED 1.00]
- **Verification approaches compared in cost vs. capability** — seminar_qa_slide_11_handwritten_suite, seminar_qa_slide_11_random_plus_golden_model, seminar_qa_slide_11_formal_verification, seminar_qa_slide_11_patara_self_testing [EXTRACTED 1.00]
- **c32 core configuration file set (core, CSR grouping, custom, ISA)** — c_class_sample_config_c32_core64, c_class_sample_config_c32_csr_grouping64, c_class_sample_config_c32_rv64i_custom, c_class_sample_config_c32_rv64i_isa [INFERRED 0.85]
- **c32_imacsu core configuration file set (core, CSR grouping, custom, debug, ISA)** — c_class_sample_config_c32_imacsu_core32, c_class_sample_config_c32_imacsu_csr_grouping32, c_class_sample_config_c32_imacsu_rv32i_custom, c_class_sample_config_c32_imacsu_rv32i_debug, c_class_sample_config_c32_imacsu_rv32i_isa [INFERRED 0.85]
- **Core configuration variants (c32_imafc, c32_imafcsu, c64, c64_debug)** — c_class_sample_config_c32_imafc_core32, c_class_sample_config_c32_imafcsu_core32, c_class_sample_config_c64_core64, c_class_sample_config_c64_debug_core64 [INFERRED 0.85]
- **customcontrol CSR (0x800) configurations across sample configs** — c_class_sample_config_c32_imafc_rv32i_custom_customcontrol, c_class_sample_config_c32_imafcsu_rv32i_custom_customcontrol, c_class_sample_config_c64_rv64i_custom_customcontrol, c_class_sample_config_c64_debug_rv64i_custom_customcontrol [INFERRED 0.85]
- **Debug CSR (dcsr) configurations across sample configs** — c_class_sample_config_c32_imafc_rv32i_debug_dcsr, c_class_sample_config_c32_imafcsu_rv32i_debug_dcsr, c_class_sample_config_c64_rv64i_debug_dcsr, c_class_sample_config_c64_debug_rv64i_debug_dcsr [INFERRED 0.85]
- **Approaches that decide correctness via a reference simulator** — seminar_seminarppt_papers_functional_verification_of_a_risc_v_vector_accelerator, seminar_seminarppt_papers_instiller_toward_efficient_and_realistic_rtl_fuzzing, seminar_03_supporting_papers_spike_golden_model [INFERRED 0.85]
- **h64 CSR configuration file set (isa, custom, debug, grouping)** — c_class_sample_config_h64_rv64i_isa, c_class_sample_config_h64_rv64i_custom, c_class_sample_config_h64_rv64i_debug, c_class_sample_config_h64_csr_grouping64 [INFERRED 0.85]
- **Top-level RV64 core configuration file set (core, CSR grouping, custom, ISA)** — c_class_sample_config_core64, c_class_sample_config_csr_grouping64, c_class_sample_config_rv64i_custom, c_class_sample_config_rv64i_isa [INFERRED 0.85]
- **RISC-V verification related work around the base paper** — seminar_qa_slide_18_gesper_selftesting_framework, seminar_qa_slide_18_rvformal, seminar_qa_slide_18_jimenez_vector_accelerator, seminar_qa_slide_18_instiller, seminar_qa_slide_18_weingarten_polynomial_formal [INFERRED 0.85]
- **Explainable-AI crop recommendation papers (LIME-based)** — seminar_ref_final1_paper2_ml_xai_crop_recommendation, seminar_ref_final1_paper3_xai_crop, seminar_ref_final1_lime [INFERRED 0.85]
- **Golden-model-free verification approaches (REVERSI, twin method, self-checking tests)** — seminar_qa_slide_15_reversi_self_test, seminar_qa_slide_15_twin_method, seminar_qa_slide_15_what_it_enables [INFERRED 0.85]

## Communities (96 total, 30 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.06
Nodes (55): Seminar Abstract (converted docx), Seminar Papers Summary table (converted docx), PATARA Full Explainer (base paper notes), Cache miss generation, Official RISC-V compliance suite, Condition coverage metric (79.12% to 100%), 100% coverage does not imply correctness, Custom ISA extension support (Section 4.2) (+47 more)

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (43): class_name(), ClassDiagram, generate mermaid code that represent the inheritance of classes defined in a…, Return a string representing the class, # NOTE: can be changed to str(class) for more complete class info, figure_wrapper(), html_visit_mermaid(), latex_visit_mermaid() (+35 more)

### Community 2 - "Community 2"
Cohesion: 0.06
Nodes (41): h64 bsc_compile_options (top_dir test_soc/c64_c32), h64 csr_grouping64.yaml, h64 CSR grp1 (M/S/H/VS CSRs, counters, PMP, custom), h64 CSR grp2 (debug CSRs, HPM counters/events), h64 rv64i_custom.yaml, h64 customcontrol CSR (0x800), h64 dtim_base/itim_base CSRs, h64 rv64i_debug.yaml (+33 more)

### Community 3 - "Community 3"
Cohesion: 0.06
Nodes (38): c32_imacsu/core32 bsc_compile_options (sim, mkTbSoc), core32.yaml (RV32 core build config), core32 bsc_compile_options (sim, mkTbSoc), core32 dcache_configuration (64 sets, 4 ways, RR), core32 icache_configuration (64 sets, 4 ways, RANDOM), core32 verilator_configuration, core64.yaml (RV64IM core build config), core64 bsc_compile_options (+30 more)

### Community 4 - "Community 4"
Cohesion: 0.07
Nodes (34): c32_imafc core32.yaml (core config), c32_imafc gshare branch predictor (btb 32, bht 512, ras 8), c32_imafc BSC compile options (mkTbSoc, AXI4, sim target), c32_imafc dcache config (64 sets, 2 ways, RR replacement), c32_imafc icache config (64 sets, 4 ways, RANDOM replacement), c32_imafc M extension (mul 2+2 stages, div 32 stages, hardfloat), c32_imafc csr_grouping32.yaml, c32_imafc CSR group grp1 (machine + FP CSRs) (+26 more)

### Community 5 - "Community 5"
Cohesion: 0.07
Nodes (34): c64 core64.yaml (core config), c64 gshare branch predictor (btb 32, bht 512, ras 8), c64 BSC compile options and AXI4 64-bit bus config, c64 dcache config (64 sets, 8-byte words, 4 ways, RR), c64 icache config (64 sets, 4 ways, RANDOM replacement), c64 M extension (mul 1+1 stages, div 32 stages), c64 csr_grouping64.yaml, c64 CSR group grp1 (M/S/PMP/FP/custom CSRs) (+26 more)

### Community 6 - "Community 6"
Cohesion: 0.11
Nodes (27): Seminar QA Grid A (slides 1-18 contact sheet), BDD equivalence checking with proven polynomial time bounds, PATARA extension: cache-miss generation, Comparison with alternate approaches (why PATARA was chosen), Coverage-guided fuzzing with Ant Colony Optimization (VACO) and ISS differential check, Golden reference model, PATARA extension: pipeline hazard sequence generation, INSTILLER: Toward Efficient and Realistic RTL Fuzzing (Zhang et al., 2024) (+19 more)

### Community 7 - "Community 7"
Cohesion: 0.09
Nodes (26): h64 core64.yaml (hypervisor-capable core config), h64 branch_predictor (gshare, btb 32, bht 512, ras 8), h64 bus_protocol_configuration (AXI4, 64-bit), h64 dcache_configuration (64 sets, 4 ways, 1rw), h64 icache_configuration (64 sets, 4 ways), h64 isb_sizes (inter-stage buffers s0s1..s4s5), h64 m_extension (mul_stages_in/out 1, div 32), h64 noinline_modules (per-stage/box BSV modules kept separate) (+18 more)

### Community 8 - "Community 8"
Cohesion: 0.11
Nodes (24): debug64 core64.yaml (RV64IM core config), debug64 bsc_compile_options (mkTbSoc sim build), debug64 dcache_configuration (64 sets, 4 ways, RR), debug64 debugger_support flag (false, 0 triggers), debug64 icache_configuration (64 sets, 4 ways, RANDOM), debug64 m_extension (mul 1 stage, div 32 stages), debug64 verilator_configuration, debug64 csr_grouping64.yaml (+16 more)

### Community 9 - "Community 9"
Cohesion: 0.10
Nodes (23): AAL atlas (Automated Anatomical Labelling), ALFF (Amplitude of Low-Frequency Fluctuation), Amplitude Envelope Correlation, Base paper: Aberrant Amplitude of Low-Frequency Fluctuations in Different Frequency Bands in PD (fMRI, Wang et al. 2020), fNIRS change in light absorption formula, Clinical assessment scales (UPDRS-III, Hoehn & Yahr, MMSE, LEDD), EEG (scalp) modality, Fast Fourier Transform (FFT) (+15 more)

### Community 10 - "Community 10"
Cohesion: 0.12
Nodes (20): Seminar Presentation: Automated Segmentation of Cardiac MRI Using Improved U-Net (U-Net-CSP), 3-D Heart Reconstruction from segmented slices, Base paper dataset (180 patients, 3600 ED/ES images, Siemens SSFP), Canny Edge Detection, Cardiac MRI (LV, RV, Aorta segmentation), Convolutional Block Attention Module (CBAM), Base Paper: Chen et al. (2023) U-Net + CSP, Combined Loss (weighted CE + Dice + boundary term) (+12 more)

### Community 11 - "Community 11"
Cohesion: 0.17
Nodes (18): BPU (Branch Prediction Unit), AXI4 / AXI4-Lite / TileLink-U Bus Fabric (configurable), Bypass Logic, Data Cache / Data TLB, Decode stage, Execution stage, FPU, Instr Cache / Instr TLB (+10 more)

### Community 12 - "Community 12"
Cohesion: 0.14
Nodes (18): Seminar deck: Recommendation Systems in Smart Agriculture (slides 1-12), Crop dataset (N, P, K, temperature, humidity, pH, rainfall), Enhanced Gaussian Naive Bayes (EGNB), 99.55% accuracy, Random Forest + Flask web deployment, Gradient Boosting (best model, 99.27% accuracy), IoT pipeline: sensors, Arduino Nano, ESP32, Blynk cloud, ML models, best crop, LIME explainability, Literature Survey table (5 papers, 2024-2026) (+10 more)

### Community 13 - "Community 13"
Cohesion: 0.17
Nodes (16): Seminar Deck: Verification Methodologies for RISC-V Processors (slide grid), Cache-miss generation extension, Official RISC-V compliance suite (79.12% condition coverage baseline), PATARA experimental results (79.12% to 100% condition coverage), Golden reference model dependency problem, Pipeline hazard-sequence generation, INSTILLER: Toward Efficient and Realistic RTL Fuzzing (Zhang et al. 2024), Operand swapping extension (+8 more)

### Community 14 - "Community 14"
Cohesion: 0.14
Nodes (15): c32_imacsu/rv32i_isa pmpcfg0-3 / pmpaddr0-15 CSRs, c32_imacsu/rv32i_isa satp CSR (Sv32), default32.yaml (RV32IMACFSU build config), default32 branch_predictor (gshare, btb 32, bht 512), default32 csr_configuration (daisy structure), default32 dcache_configuration (word_size 8), default32 ISA: RV32IMACFSU, default32 pmp (4 entries, granularity 8) (+7 more)

### Community 15 - "Community 15"
Cohesion: 0.14
Nodes (14): mulAddRecFN, mulAddRecFNToRaw, mulAddRecFNToRaw_postMul, mulAddRecFNToRaw_preMul, countLeadingZeros, isSigNaNRecFN, recFNToRawFN, roundRawFNToRecFN (+6 more)

### Community 16 - "Community 16"
Cohesion: 0.16
Nodes (15): Slide 09: Supporting Papers - At a Glance, Base paper (removes reference-model dependency), BDD equivalence checking (oracle), Constrained-random test generation, Coverage-guided fuzzing, Exhaustive (formal) test generation, INSTILLER, ISS differential testing (oracle) (+7 more)

### Community 17 - "Community 17"
Cohesion: 0.22
Nodes (13): Base paper role, BDD equivalence checking with proven time bounds, High-level (Chisel) formal model checking, Coverage-guided RTL fuzzing (ant-colony), INSTILLER: Toward Efficient and Realistic RTL Fuzzing (Zhang et al.), Literature Survey Overview (slide 4), Polynomial Formal Verification of a RISC-V Processor (Weingarten et al.), Functional Verification of a RISC-V Vector Accelerator (Jiménez et al.) (+5 more)

### Community 18 - "Community 18"
Cohesion: 0.26
Nodes (4): glob, os, re, sys

### Community 19 - "Community 19"
Cohesion: 0.20
Nodes (12): c32/core64.yaml (c32 core build config, fpga target), c32/core64 branch_predictor (gshare, btb 32, bht 512), c32/core64 bsc_compile_options (fpga, mktest_instances), c32/core64 dcache_configuration, c32/core64 icache_configuration, c32_imacsu/core32.yaml (IMACSU core build config), c32_imacsu/core32 branch_predictor (gshare, btb 8, bht 128), c32_imacsu/core32 bus_protocol_configuration (AXI4, 32-bit) (+4 more)

### Community 20 - "Community 20"
Cohesion: 0.21
Nodes (12): c32_imacsu/rv32i_isa.yaml (RV32IMACSU CSR ISA spec), c32_imacsu/rv32i_isa custom_exceptions (halt_ebreak, halt_trigger, halt_step, halt_reset), c32_imacsu/rv32i_isa custom_interrupts (debug_interrupt), c32_imacsu/rv32i_isa mcounteren / scounteren / menvcfg / senvcfg CSRs, c32_imacsu/rv32i_isa mstatus CSR, c32/rv64i_isa.yaml (RV32IMSU CSR ISA spec), c32/rv64i_isa custom_exceptions (halt_ebreak, halt_trigger, halt_step, halt_reset), c32/rv64i_isa custom_interrupts (debug_interrupt) (+4 more)

### Community 21 - "Community 21"
Cohesion: 0.18
Nodes (12): c32iamfc_deps.yaml (SHAKTI c32 IAMFC dependency pins), caches_mmu 14.3.0 (c32iamfc), csrbox 1.11.0 (c32iamfc), devices 109-32bit_with_clock_gating (c32iamfc), riscv-config 3.7.0 (c32iamfc), verification 5.0.5 with cclass-env.patch (c32iamfc), c32imacsu_deps.yaml (SHAKTI c32 IMACSU dependency pins), caches_mmu 14.4.3 (c32imacsu) (+4 more)

### Community 22 - "Community 22"
Cohesion: 0.20
Nodes (12): Slide 16: Comparison with Alternate Approaches, BDD-based formal verification, Coverage-guided fuzzing, High-level formal verification (bounded depth 40, 7 real bugs), INSTILLER, PATARA (base paper), PFV, Self-testing verification without golden model (+4 more)

### Community 23 - "Community 23"
Cohesion: 0.24
Nodes (11): Bugs PATARA found, Cache miss during multiply bug, Cache-miss / stall combinations bug, Condition coverage (79.12% vs 100%), Co-processor (V2PRO) twin method, Forwarding during multi-cycle divide bug, Load to JALR forwarding bug, Official compliance suite (+3 more)

### Community 24 - "Community 24"
Cohesion: 0.22
Nodes (11): Slide 06: Literature Survey Paper 2 - Functional Verification of a RISC-V Vector Accelerator, Functional Verification of a RISC-V Vector Accelerator (Jimenez et al., IEEE Design & Test 2023, European Processor Initiative), Key findings: 3,005 errors found in ~1 year, 95.79% functional coverage, chip taped out, 24 to 600 tests/night, Limitations: code coverage 72.64% (49.83% toggle), deprecated RVV 0.7.1, experience report not new algorithm, Memory / narrowing / widening ops account for ~70% of failures, Relevance: can an industrial UVM flow verify a taped-out vector coprocessor?, Google RISCV-DV constrained-random generation + Jenkins CI, Role: industrial golden-model practice, the opposite of the base paper (+3 more)

### Community 25 - "Community 25"
Cohesion: 0.22
Nodes (11): Coverage-guided fuzzing with ISS vs RTL differential check, DiFuzzRTL (baseline tool), Hardware-aware seed selection and mutation, INSTILLER: Toward Efficient & Realistic RTL Fuzzing, Realistic multi-interrupt and exception injection with priorities, Key findings: +29.4% coverage, +17.0% mismatches, 79.3% shorter inputs, +6.7% speed, Limitations: OpenRISC cores, candidate bugs only, cannot prove absence of bugs, Relevance: short tests covering interrupt corner cases in CPU fuzzing (+3 more)

### Community 26 - "Community 26"
Cohesion: 0.29
Nodes (10): Slide 05: chiRVFormal literature survey paper 1, BOOM out-of-order scaling result (1,953 s vs 22,855 s), 7 designer-confirmed bugs found (riscv-formal found 2), chiRVFormal: Formal Verification of RISC-V Chisel Designs, Formal-methods pillar (ISA conformance proof), High-level Chisel reference model of RISC-V, Limitations: bounded depth 40, unverified sync mechanism, slow on small designs, Pono / SMTBMC + Boolector model checking (+2 more)

### Community 27 - "Community 27"
Cohesion: 0.29
Nodes (10): Slide 08: Literature Survey Paper 4 - Polynomial Formal Verification of a RISC-V Processor, Binary Decision Diagrams (canonical form, equivalence = pointer check), Control unit verified as FSM walk against golden reference, Entire Execute unit verified in 11.95 ms; all 32 control signals verified (up from 15), Limitations: excludes HALT/TRAP/interrupt states, finds zero bugs, closed-source tool, cannot handle pipelined cores (chiRVFormal), MicroRV32 (multi-cycle, non-pipelined RISC-V core), Polynomial Formal Verification of a RISC-V Processor (Weingarten, Datta & Drechsler, IEEE Trans. on Nanotechnology 2025, Univ. Bremen), Proven polynomial bounds: O(n) Fetch, O(n^2) Execute/Decode, O(k*m) Control (+2 more)

### Community 28 - "Community 28"
Cohesion: 0.27
Nodes (10): Slide 15: Applications & Relevance, Coverage necessary but not sufficient (100% != bug-free), Limitations: RV32IM only, no CSRs/interrupts, single design evaluated, Custom instructions have no golden reference, PATARA, REVERSI self-test (invertible ops, e.g. ADD+1), Relevance to Team 2 project (RISC-V custom AI/vector instructions for edge video anomaly detection), Transferable insight: separate test generation from correctness oracle (+2 more)

### Community 29 - "Community 29"
Cohesion: 0.22
Nodes (8): axi_ethernetlite_0, fpga_top, clk_converter, clk_divider, IOBUF, mkDebugSoc, proc_sys_reset_0, ddr4_0

### Community 30 - "Community 30"
Cohesion: 0.31
Nodes (8): mulRecFN, mulRecFNToFullRaw, mulRecFNToRaw, isSigNaNRecFN, recFNToRawFN, roundRawFNToRecFN, mulRecFNToRaw, propagateFloatNaN_mul

### Community 31 - "Community 31"
Cohesion: 0.22
Nodes (8): fpga_top, BSCANE2, clk_converter, clk_divider, IOBUF, mkDebugSoc, proc_sys_reset_0, mig_ddr3

### Community 32 - "Community 32"
Cohesion: 0.22
Nodes (8): fpga_top, BSCANE2, clk_converter, clk_divider, IOBUF, mkDebugSoc, proc_sys_reset_0, vcu108mig

### Community 33 - "Community 33"
Cohesion: 0.22
Nodes (8): fpga_top, BSCANE2, clk_converter, clk_divider, IOBUF, mkDebugSoc, proc_sys_reset_0, vcu118mig

### Community 34 - "Community 34"
Cohesion: 0.28
Nodes (9): Slide 02: Agenda (01 Overview), Agenda item 4: Applications & Relevance, Agenda item 5: Comparison with Alternate Approaches, Agenda item 6: Conclusion, Agenda item 1: Introduction & Objective, Agenda item 3: Literature Survey - Base Paper (deep dive), Agenda item 2: Literature Survey - Supporting Papers, 5 peer-reviewed papers (4 supporting + 1 base), SCOPUS/SCIE indexed 2023-2026 (+1 more)

### Community 35 - "Community 35"
Cohesion: 0.42
Nodes (9): Slide 04: Survey Overview (Literature Survey), Formal verification approaches (model checking, BDD equivalence), Golden-model co-simulation (Spike reference), INSTILLER (Zhang et al., 2024) - coverage-guided RTL fuzzing (ant-colony), PATARA (Gesper et al., 2026) - self-testing (REVERSI), no golden model; BASE PAPER, Polynomial Formal Verification (Weingarten et al., 2025) - BDD equivalence checking with proven time bounds, RISC-V Vector Accelerator (Jiménez et al., 2023) - UVM co-simulation vs Spike golden model, Self-testing (REVERSI) without golden model (+1 more)

### Community 36 - "Community 36"
Cohesion: 0.28
Nodes (9): Slide 16: Comparison with Alternate Approaches, Golden reference model, INSTILLER (coverage-guided fuzzing; short tests; incomplete, 2 non-RISC-V cores), PATARA (base paper; self-testing, no golden model, 100% coverage, post-silicon; RV32IM, no CSR/interrupts), PFV (BDD-based formal; proven runtime bound, complete; non-pipelined toy core), Self-testing verification approach, Vector Accelerator verification (UVM + golden model; 3,005 bugs, taped out; code coverage only 72.6%), Why the base paper was chosen (+1 more)

### Community 37 - "Community 37"
Cohesion: 0.31
Nodes (9): Slide 11: The Problem Being Addressed (Base Paper), Cost vs. capability trade-off, Formal verification, Why a golden model hurts, Handwritten suite, Naive approach: handwritten RISC-V compliance suite, PATARA (self-testing), Random + golden model (+1 more)

### Community 38 - "Community 38"
Cohesion: 0.33
Nodes (9): Slide 17: Conclusion, Formal methods (chiRVFormal, PFV): complete guarantees but trade scalability or completeness, Golden reference model dependency, Coverage-guided fuzzing (INSTILLER), PATARA (base paper): systematic test generation with self-checking execution, PATARA result: 100% condition coverage vs 79.12% for compliance suite, Project path: self-testing and twin-based verification, extend to floating-point and privileged mode, RISC-V verification splits along two axes: test source and correctness decision (+1 more)

### Community 39 - "Community 39"
Cohesion: 0.32
Nodes (8): c32_imacsu/csr_grouping32.yaml (CSR grouping), c32_imacsu/csr_grouping32 grp1 (M/S-mode, PMP, CUSTOMCONTROL), c32_imacsu/csr_grouping32 grp2 (debug CSRs, HPM counters), c32_imacsu/rv32i_custom.yaml (custom CSR spec), c32_imacsu/rv32i_custom customcontrol CSR (with debug_enable), c32_imacsu/rv32i_debug.yaml (Debug spec 1.0.0), c32_imacsu/rv32i_debug dcsr CSR, c32_imacsu/rv32i_debug dpc / dscratch0 / dscratch1 CSRs

### Community 40 - "Community 40"
Cohesion: 0.29
Nodes (8): setup-cowork skill (guided Cowork setup), Organization plugins take priority, Cowork setup flow (role, plugins, connectors, try skill, writing voice, wrap), setup-writing-style skill (voice profile builder), Consent-first and no-PII guardrails, my-writing-style profile skill (VOICE.md), stylometry.py analysis script, Voice / tone / surface model

### Community 41 - "Community 41"
Cohesion: 0.36
Nodes (8): Slide 10: PATARA base paper overview, Official RISC-V compliance suite, Condition coverage 79.12% to 100% headline result, Pipeline hazard-sequence generator and cache-miss generation (operand swapping), PATARA self-testing framework for RISC-V + co-processor, REVERSI self-test generation ported to RISC-V, Self-checking tests without external golden model, Twin-based co-processor verification

### Community 42 - "Community 42"
Cohesion: 0.36
Nodes (8): Extension 3: Cache-miss generation (96.7 to 100%), Verified RISC-V core as golden model, Extension 2: Hazard sequences (81 to 96.7%), Extension 1: Operand swapping (FSM 88.6 to 94.3%), REVERSI (inversion-based self-checking), Slide 13: Framework & Four Extensions (Base Paper), Extension 4: Twin-based co-processor verification, XML flow (processor + ISA described in XML, ISA-independent, 80.21%)

### Community 43 - "Community 43"
Cohesion: 0.36
Nodes (8): Slide 18: References, Gesper et al. - Self-Testing Framework for V&V of a RISC-V System with Co-processor (BASE PAPER, 2026), Zhang et al. - INSTILLER: Efficient and Realistic RTL Fuzzing (2024), Jiménez et al. - Functional Verification of a RISC-V Vector Accelerator (2023), REVERSI: Post-silicon validation via self-checking randomized programs, The RISC-V Instruction Set Manual, Volume I: Unprivileged ISA (2019), Shen et al. - χRVFormal: Formal verification of RISC-V Chisel designs (2026), Weingarten et al. - Polynomial Formal Verification of a RISC-V Processor (2025)

### Community 44 - "Community 44"
Cohesion: 0.52
Nodes (7): Compare Focus and Target register (beq t2, t1, SUCCESS), Focus register (t1), Modification Operation (add t2, t1, t0), Random register (t0), Restoring Operation (sub t2, t2, t0), Slide 11: RISC-V register restore-and-compare test snippet, Target register (t2)

### Community 45 - "Community 45"
Cohesion: 0.43
Nodes (7): Slide 03: Introduction & Motivation, Compliance suite gap, Core challenge: no golden answer for an invented instruction, Trade-off axis: how correctness is decided (golden model / self-check / proof), Objective: review 5 papers on RISC-V verification evolution, RISC-V open extensible ISA with custom instructions, Trade-off axis: where tests come from (systematic / random / none)

### Community 46 - "Community 46"
Cohesion: 0.38
Nodes (7): Slide 12: Core Mechanism - REVERSI, Step 3 Comparison: recovered == focus ?, Mismatch indicates hardware error, Step 1 Modification: target = focus XOR random, Step 2 Restoring: recovered = target inverse-op random, REVERSI self-test, Reversible operation needs no reference model

### Community 47 - "Community 47"
Cohesion: 0.33
Nodes (7): Slide 16: Comparison with Alternate Approaches, Why the base paper was chosen, INSTILLER, PATARA (base paper), PFV, Vector Accelerator (UVM + golden model), χRVFormal

### Community 48 - "Community 48"
Cohesion: 0.33
Nodes (6): c32/csr_grouping64.yaml (CSR grouping), c32/csr_grouping64 grp1 (M/S-mode CSRs), c32/csr_grouping64 grp2 (PMP, CUSTOMCONTROL), c32/rv64i_custom.yaml (custom CSR spec), c32/rv64i_custom customcontrol CSR (with debug_enable), c32/rv64i_custom dtim_base / itim_base CSRs

### Community 49 - "Community 49"
Cohesion: 0.33
Nodes (5): iNToRawFN, iNToRecFN, countLeadingZeros, roundAnyRawFNToRecFN, iNToRawFN

### Community 50 - "Community 50"
Cohesion: 0.33
Nodes (3): sim_main, verilated, verilated_vcd_c

### Community 51 - "Community 51"
Cohesion: 0.33
Nodes (6): Cache tests (full PATARA): 6,732,901 instr, 100.00%, Compliance suite (baseline): 889,516 instr, 79.12% condition cov, Ablation: removing hazard-sequence generation drops coverage to 81.31%, Compliance suite found 0 bugs; PATARA exposed 4 categories of real hazard bugs, Hazard sequences: 1,851,852 instr, 96.70%, PATARA (full test generator)

### Community 52 - "Community 52"
Cohesion: 0.33
Nodes (6): Slide 14: Experimental Results (PATARA base paper), Cache tests config (6,732,901 instr, 100.00%), Compliance suite baseline (889,516 instr, 79.12% condition cov), Condition coverage metric (Questa Sim), DUT: 6-stage RV32IM core + V2PRO vector co-processor, PATARA (full, with cache tests)

### Community 53 - "Community 53"
Cohesion: 0.40
Nodes (3): countLeadingZeros, prio_enc, reverse

### Community 54 - "Community 54"
Cohesion: 0.40
Nodes (4): div_sqrt, fNToRecFN, recFNToFN, divSqrtRecFN_small

### Community 55 - "Community 55"
Cohesion: 0.40
Nodes (4): ftof, fNToRecFN, recFNToFN, recFNToRecFN

### Community 56 - "Community 56"
Cohesion: 0.40
Nodes (4): mulAdd, fNToRecFN, recFNToFN, mulAddRecFN

### Community 57 - "Community 57"
Cohesion: 0.40
Nodes (5): Seminar title slide: Verification Methodologies for RISC-V Processors, Dept. of Computer Science & Engineering, Kevin Jose (presenter), RISC-V open extensible processor implementations, Verification Methodologies for RISC-V Processors

### Community 58 - "Community 58"
Cohesion: 0.50
Nodes (3): compareRecFN, isSigNaNRecFN, recFNToRawFN

### Community 59 - "Community 59"
Cohesion: 0.50
Nodes (3): ftoi, fNToRecFN, recFNToIN

### Community 60 - "Community 60"
Cohesion: 0.50
Nodes (3): itof, recFNToFN, iNToRecFN

### Community 61 - "Community 61"
Cohesion: 0.50
Nodes (3): recFNToIN, recFNToRawFN, iNFromException

### Community 62 - "Community 62"
Cohesion: 0.50
Nodes (3): recFNToRecFN, isSigNaNRecFN, recFNToRawFN

### Community 63 - "Community 63"
Cohesion: 0.50
Nodes (4): schedule skill (scheduled task creation), create_scheduled_task tool, Self-contained task prompt, update_scheduled_task tool

### Community 64 - "Community 64"
Cohesion: 0.50
Nodes (4): Instruction combinations: 6,983 instr, 80.21%, Interleaving: 17,294 instr, 81.31%, Key observations: +20.88 pts, 127x fewer instructions, interleaving adds 0.00 pts, Operand switching: 9,722 instr, 81.31%

### Community 74 - "Community 74"
Cohesion: 0.67
Nodes (3): Slide 14: Experimental Results (Base Paper), Condition coverage metric (Questa Sim), DUT: 6-stage RV32IM core + V2PRO vector co-processor

## Knowledge Gaps
- **306 isolated node(s):** `setup.sh script`, `c32_imafcsu_sim.sh script`, `SOC`, `c64_sim.sh script`, `c64_tsoc_sim.sh script` (+301 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 404 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **30 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `c64_deps.yaml (SHAKTI c64 dependency pins)` connect `Community 2` to `Community 21`?**
  _High betweenness centrality (0.004) - this node is a cross-community bridge._
- **Why does `c32_imacsu/rv32i_isa.yaml (RV32IMACSU CSR ISA spec)` connect `Community 20` to `Community 19`, `Community 14`, `Community 39`?**
  _High betweenness centrality (0.004) - this node is a cross-community bridge._
- **Why does `h64 core64.yaml (hypervisor-capable core config)` connect `Community 7` to `Community 2`?**
  _High betweenness centrality (0.004) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `Slide-by-Slide Content (18-slide deck)` (e.g. with `Seven-part deck structure with consistent per-paper micro-structure` and `Seminar Speaking Script`) actually correct?**
  _`Slide-by-Slide Content (18-slide deck)` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `setup.sh script`, `c32_imafcsu_sim.sh script`, `SOC` to the rest of the system?**
  _306 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.06464646464646465 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.05587808417997097 - nodes in this community are weakly interconnected._