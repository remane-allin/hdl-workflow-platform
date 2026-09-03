# Additional clean files
cmake_minimum_required(VERSION 3.16)

if("${CONFIG}" STREQUAL "" OR "${CONFIG}" STREQUAL "")
  file(REMOVE_RECURSE
  "G:\\EEG\\Workflow\\prj\\eeg_2or8to2or16\\output\\vitis\\p1_eeg_platform\\ps7_cortexa9_0\\p1_eeg_standalone\\bsp\\include\\sleep.h"
  "G:\\EEG\\Workflow\\prj\\eeg_2or8to2or16\\output\\vitis\\p1_eeg_platform\\ps7_cortexa9_0\\p1_eeg_standalone\\bsp\\include\\xiltimer.h"
  "G:\\EEG\\Workflow\\prj\\eeg_2or8to2or16\\output\\vitis\\p1_eeg_platform\\ps7_cortexa9_0\\p1_eeg_standalone\\bsp\\include\\xtimer_config.h"
  "G:\\EEG\\Workflow\\prj\\eeg_2or8to2or16\\output\\vitis\\p1_eeg_platform\\ps7_cortexa9_0\\p1_eeg_standalone\\bsp\\lib\\libxiltimer.a"
  )
endif()
