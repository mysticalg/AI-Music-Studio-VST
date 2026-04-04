cmake_minimum_required(VERSION 3.22)

project(AdvancedVSTi VERSION 0.2.0)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(NOT DEFINED JUCE_DIR)
  message(FATAL_ERROR "Set -DJUCE_DIR=/path/to/JUCE")
endif()

add_subdirectory(${JUCE_DIR} JUCE)

set(AIMS_REPO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}")
get_filename_component(AIMS_REPO_ROOT "${AIMS_REPO_ROOT}" ABSOLUTE)
set(AIMS_HOST_REPO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../..")
get_filename_component(AIMS_HOST_REPO_ROOT "${AIMS_HOST_REPO_ROOT}" ABSOLUTE)
set(AIMS_REPO_PARENT "${AIMS_REPO_ROOT}/..")
get_filename_component(AIMS_REPO_PARENT "${AIMS_REPO_PARENT}" ABSOLUTE)

function(aims_resolve_cache_dir out_var folder_name)
  set(resolved_dir "")

  foreach(candidate
      "${AIMS_REPO_ROOT}/.cache/${folder_name}"
      "${AIMS_HOST_REPO_ROOT}/.cache/${folder_name}")
    if(EXISTS "${candidate}")
      set(resolved_dir "${candidate}")
      break()
    endif()
  endforeach()

  if(NOT resolved_dir)
    file(GLOB aims_repo_siblings LIST_DIRECTORIES true "${AIMS_REPO_PARENT}/*")
    foreach(sibling_dir ${aims_repo_siblings})
      if(EXISTS "${sibling_dir}/.cache/${folder_name}")
        set(resolved_dir "${sibling_dir}/.cache/${folder_name}")
        break()
      endif()
    endforeach()
  endif()

  set(${out_var} "${resolved_dir}" PARENT_SCOPE)
endfunction()

set(AIMS_BINARY_DATA_PLACEHOLDER "${CMAKE_CURRENT_SOURCE_DIR}/Source/BinaryDataPlaceholder.txt")
set(AIMS_ASSET_SOURCES "${AIMS_BINARY_DATA_PLACEHOLDER}")
set(AIMS_HAS_TR909_IMAGE 0)
set(AIMS_VEC1_LIBRARY_DIR "D:/OneDrive/Music/Sound Design/Sample Library/sample library/VEC1" CACHE PATH "Path to the optional VEC1 sample library.")
set(AIMS_PIANO_LIBRARY_DIR "" CACHE PATH "Path to the optional Splendid Grand Piano library.")
set(AIMS_OPEN_INSTRUMENT_SAMPLES_DIR "" CACHE PATH "Path to the optional OpenInstrumentSamples library root.")
set(AIMS_VEC1_EFFECTIVE_LIBRARY_DIR "${AIMS_VEC1_LIBRARY_DIR}")
if(NOT EXISTS "${AIMS_VEC1_EFFECTIVE_LIBRARY_DIR}")
  aims_resolve_cache_dir(AIMS_VEC1_AUTODETECTED_LIBRARY_DIR "VEC1")
  if(EXISTS "${AIMS_VEC1_AUTODETECTED_LIBRARY_DIR}")
    set(AIMS_VEC1_EFFECTIVE_LIBRARY_DIR "${AIMS_VEC1_AUTODETECTED_LIBRARY_DIR}")
  endif()
endif()
set(AIMS_PIANO_EFFECTIVE_LIBRARY_DIR "${AIMS_PIANO_LIBRARY_DIR}")
if(NOT EXISTS "${AIMS_PIANO_EFFECTIVE_LIBRARY_DIR}")
  aims_resolve_cache_dir(AIMS_PIANO_AUTODETECTED_LIBRARY_DIR "SplendidGrandPiano")
  if(EXISTS "${AIMS_PIANO_AUTODETECTED_LIBRARY_DIR}")
    set(AIMS_PIANO_EFFECTIVE_LIBRARY_DIR "${AIMS_PIANO_AUTODETECTED_LIBRARY_DIR}")
  endif()
endif()
set(AIMS_OPEN_INSTRUMENT_SAMPLES_EFFECTIVE_LIBRARY_DIR "${AIMS_OPEN_INSTRUMENT_SAMPLES_DIR}")
if(NOT EXISTS "${AIMS_OPEN_INSTRUMENT_SAMPLES_EFFECTIVE_LIBRARY_DIR}")
  aims_resolve_cache_dir(AIMS_OPEN_INSTRUMENT_SAMPLES_AUTODETECTED_LIBRARY_DIR "OpenInstrumentSamples")
  if(EXISTS "${AIMS_OPEN_INSTRUMENT_SAMPLES_AUTODETECTED_LIBRARY_DIR}")
    set(AIMS_OPEN_INSTRUMENT_SAMPLES_EFFECTIVE_LIBRARY_DIR "${AIMS_OPEN_INSTRUMENT_SAMPLES_AUTODETECTED_LIBRARY_DIR}")
  endif()
endif()
set(AIMS_VEC1_EFFECTIVE_LIBRARY_DIR "${AIMS_VEC1_EFFECTIVE_LIBRARY_DIR}" CACHE INTERNAL "Resolved path to the VEC1 sample library." FORCE)
set(AIMS_PIANO_EFFECTIVE_LIBRARY_DIR "${AIMS_PIANO_EFFECTIVE_LIBRARY_DIR}" CACHE INTERNAL "Resolved path to the Splendid Grand Piano library." FORCE)
set(AIMS_OPEN_INSTRUMENT_SAMPLES_EFFECTIVE_LIBRARY_DIR "${AIMS_OPEN_INSTRUMENT_SAMPLES_EFFECTIVE_LIBRARY_DIR}" CACHE INTERNAL "Resolved path to the OpenInstrumentSamples library." FORCE)
set(AIMS_TR909_IMAGE "${AIMS_REPO_ROOT}/tr9092.jpg")
if(NOT EXISTS "${AIMS_TR909_IMAGE}" AND EXISTS "${AIMS_HOST_REPO_ROOT}/tr9092.jpg")
  set(AIMS_TR909_IMAGE "${AIMS_HOST_REPO_ROOT}/tr9092.jpg")
endif()
if(EXISTS "${AIMS_TR909_IMAGE}")
  list(APPEND AIMS_ASSET_SOURCES "${AIMS_TR909_IMAGE}")
  set(AIMS_HAS_TR909_IMAGE 1)
endif()
juce_add_binary_data(AIMusicStudioVirusAssets SOURCES ${AIMS_ASSET_SOURCES})

option(AIMS_BUILD_SCREENSHOT_EXPORTERS "Build helper executables that render UI screenshots for the GitHub Pages catalog." OFF)

function(add_ai_music_vst3 target_name product_name plugin_code flavor_code bundle_id)
  juce_add_plugin(${target_name}
      COMPANY_NAME "AI Music Studio"
      BUNDLE_ID ${bundle_id}
      IS_SYNTH TRUE
      NEEDS_MIDI_INPUT TRUE
      NEEDS_MIDI_OUTPUT FALSE
      IS_MIDI_EFFECT FALSE
      EDITOR_WANTS_KEYBOARD_FOCUS FALSE
      COPY_PLUGIN_AFTER_BUILD FALSE
      PLUGIN_MANUFACTURER_CODE AIms
      PLUGIN_CODE ${plugin_code}
      FORMATS VST3 Standalone
      PRODUCT_NAME "${product_name}")

  juce_generate_juce_header(${target_name})

  target_sources(${target_name}
      PRIVATE
        Source/PluginProcessor.cpp
        Source/PluginProcessor.h
        Source/PluginEditor.cpp
        Source/PluginEditor.h)

  target_compile_definitions(${target_name}
    PRIVATE
      AIMS_INSTRUMENT_FLAVOR=${flavor_code}
      AIMS_HAS_TR909_IMAGE=${AIMS_HAS_TR909_IMAGE}
      AIMS_OPEN_INSTRUMENT_SAMPLES_PATH="${AIMS_OPEN_INSTRUMENT_SAMPLES_EFFECTIVE_LIBRARY_DIR}"
      AIMS_PIANO_LIBRARY_PATH="${AIMS_PIANO_EFFECTIVE_LIBRARY_DIR}"
      AIMS_VEC1_LIBRARY_PATH="${AIMS_VEC1_EFFECTIVE_LIBRARY_DIR}"
      AIMS_REPO_ROOT_PATH="${AIMS_REPO_ROOT}"
    PUBLIC
      JUCE_WEB_BROWSER=0
      JUCE_USE_CURL=0
      JUCE_VST3_CAN_REPLACE_VST2=0)

  target_link_libraries(${target_name}
      PRIVATE
        AIMusicStudioVirusAssets
        juce::juce_audio_utils
        juce::juce_dsp
      PUBLIC
        juce::juce_recommended_config_flags
        juce::juce_recommended_lto_flags
        juce::juce_recommended_warning_flags)
endfunction()

function(add_ai_music_fx_vst3 target_name product_name plugin_code flavor_code bundle_id)
  juce_add_plugin(${target_name}
      COMPANY_NAME "AI Music Studio"
      BUNDLE_ID ${bundle_id}
      IS_SYNTH FALSE
      NEEDS_MIDI_INPUT FALSE
      NEEDS_MIDI_OUTPUT FALSE
      IS_MIDI_EFFECT FALSE
      EDITOR_WANTS_KEYBOARD_FOCUS FALSE
      COPY_PLUGIN_AFTER_BUILD FALSE
      PLUGIN_MANUFACTURER_CODE AIms
      PLUGIN_CODE ${plugin_code}
      FORMATS VST3 Standalone
      PRODUCT_NAME "${product_name}")

  juce_generate_juce_header(${target_name})

  target_sources(${target_name}
      PRIVATE
        Source/PluginProcessor.cpp
        Source/PluginProcessor.h
        Source/PluginEditor.cpp
        Source/PluginEditor.h)

  target_compile_definitions(${target_name}
    PRIVATE
      AIMS_INSTRUMENT_FLAVOR=${flavor_code}
      AIMS_HAS_TR909_IMAGE=${AIMS_HAS_TR909_IMAGE}
      AIMS_OPEN_INSTRUMENT_SAMPLES_PATH="${AIMS_OPEN_INSTRUMENT_SAMPLES_EFFECTIVE_LIBRARY_DIR}"
      AIMS_PIANO_LIBRARY_PATH="${AIMS_PIANO_EFFECTIVE_LIBRARY_DIR}"
      AIMS_VEC1_LIBRARY_PATH="${AIMS_VEC1_EFFECTIVE_LIBRARY_DIR}"
      AIMS_REPO_ROOT_PATH="${AIMS_REPO_ROOT}"
    PUBLIC
      JUCE_WEB_BROWSER=0
      JUCE_USE_CURL=0
      JUCE_VST3_CAN_REPLACE_VST2=0)

  target_link_libraries(${target_name}
      PRIVATE
        AIMusicStudioVirusAssets
        juce::juce_audio_utils
        juce::juce_dsp
      PUBLIC
        juce::juce_recommended_config_flags
        juce::juce_recommended_lto_flags
        juce::juce_recommended_warning_flags)

  if(MSVC AND TARGET ${target_name}_Standalone)
    # MSVC emits a standalone-only false positive from JUCE sources for C4702.
    target_compile_options(${target_name}_Standalone PRIVATE /wd4702)
  endif()
endfunction()

function(add_ai_music_screenshot_exporter target_name product_name flavor_code)
  set(exporter_target "${target_name}ScreenshotExporter")

  juce_add_console_app(${exporter_target}
      PRODUCT_NAME "${product_name} Screenshot Exporter")

  juce_generate_juce_header(${exporter_target})

  target_sources(${exporter_target}
      PRIVATE
        tools/ScreenshotExporterMain.cpp
        Source/PluginProcessor.cpp
        Source/PluginProcessor.h
        Source/PluginEditor.cpp
        Source/PluginEditor.h)

  target_compile_definitions(${exporter_target}
    PRIVATE
      AIMS_INSTRUMENT_FLAVOR=${flavor_code}
      AIMS_HAS_TR909_IMAGE=${AIMS_HAS_TR909_IMAGE}
      AIMS_OPEN_INSTRUMENT_SAMPLES_PATH="${AIMS_OPEN_INSTRUMENT_SAMPLES_EFFECTIVE_LIBRARY_DIR}"
      AIMS_PIANO_LIBRARY_PATH="${AIMS_PIANO_EFFECTIVE_LIBRARY_DIR}"
      AIMS_VEC1_LIBRARY_PATH="${AIMS_VEC1_EFFECTIVE_LIBRARY_DIR}"
      AIMS_REPO_ROOT_PATH="${AIMS_REPO_ROOT}"
      JucePlugin_Name="${product_name}"
      JUCE_WEB_BROWSER=0
      JUCE_USE_CURL=0)

  target_link_libraries(${exporter_target}
      PRIVATE
        AIMusicStudioVirusAssets
        juce::juce_audio_processors
        juce::juce_audio_utils
        juce::juce_dsp
      PUBLIC
        juce::juce_recommended_config_flags
        juce::juce_recommended_lto_flags
        juce::juce_recommended_warning_flags)
endfunction()

add_ai_music_vst3(VirusSynth "Virus Synth" AdvS 0 com.aimusicstudio.virussynth)
add_ai_music_vst3(AIDrumMachine "AI Drum Machine" ADrm 1 com.aimusicstudio.aidrummachine)
add_ai_music_vst3(AIBassSynth "AI Bass Synth" ABas 2 com.aimusicstudio.aibasssynth)
add_ai_music_vst3(AILeadSynth "AI Lead Synth" ALed 4 com.aimusicstudio.aileadsynth)
add_ai_music_vst3(AIPadSynth "AI Pad Synth" APad 5 com.aimusicstudio.aipadsynth)
add_ai_music_vst3(AIPluckSynth "AI Pluck Synth" APlk 6 com.aimusicstudio.aiplucksynth)
add_ai_music_vst3(AISampler "AI Sampler" ASmp 7 com.aimusicstudio.aisampler)
add_ai_music_vst3(AIVEC1DrumPads "AI VEC1 Drum Pads" AVPD 10 com.aimusicstudio.aivec1drumpads)
add_ai_music_vst3(AIPiano "AI Piano" AIPn 11 com.aimusicstudio.aipiano)
add_ai_music_vst3(AIStrings "AI Strings" AISe 12 com.aimusicstudio.aistrings)
add_ai_music_vst3(AIViolin "AI Violin" AIVl 13 com.aimusicstudio.aiviolin)
add_ai_music_vst3(AIFlute "AI Flute" AIFt 14 com.aimusicstudio.aiflute)
add_ai_music_vst3(AISaxophone "AI Saxophone" AISx 15 com.aimusicstudio.aisaxophone)
add_ai_music_vst3(AIBassGuitar "AI Bass Guitar" AIBG 16 com.aimusicstudio.aibassguitar)
add_ai_music_vst3(AIOrgan "AI Organ" AIOr 17 com.aimusicstudio.aiorgan)
add_ai_music_fx_vst3(AIDelay "AI Delay" ADly 100 com.aimusicstudio.aidelay)
add_ai_music_fx_vst3(AIReverb "AI Reverb" ARvb 101 com.aimusicstudio.aireverb)
add_ai_music_fx_vst3(AIChorus "AI Chorus" ACho 102 com.aimusicstudio.aichorus)
add_ai_music_fx_vst3(AIFlanger "AI Flanger" AFlg 103 com.aimusicstudio.aiflanger)
add_ai_music_fx_vst3(AIPhaser "AI Phaser" APhs 104 com.aimusicstudio.aiphaser)
add_ai_music_fx_vst3(AIOverdrive "AI Overdrive" AOvd 105 com.aimusicstudio.aioverdrive)
add_ai_music_fx_vst3(AIDistortion "AI Distortion" ADst 106 com.aimusicstudio.aidistortion)
add_ai_music_fx_vst3(AICompressor "AI Compressor" ACmp 107 com.aimusicstudio.aicompressor)
add_ai_music_fx_vst3(AIAmpEmulator "AI Amp Emulator" AAmp 108 com.aimusicstudio.aiampemulator)
add_ai_music_fx_vst3(AIBitCrusher "AI Bit Crusher" ABtc 109 com.aimusicstudio.aibitcrusher)
add_ai_music_fx_vst3(AIRhythmGate "AI Rhythm Gate" ARgt 110 com.aimusicstudio.airhythmgate)
add_ai_music_fx_vst3(AIGraphicEQ "AI Graphic EQ" AGEq 111 com.aimusicstudio.aigraphiceq)
add_ai_music_fx_vst3(AIParametricEQ "AI Parametric EQ" APEq 112 com.aimusicstudio.aiparametriceq)

if(AIMS_BUILD_SCREENSHOT_EXPORTERS)
  add_ai_music_screenshot_exporter(VirusSynth "Virus Synth" 0)
  add_ai_music_screenshot_exporter(AIDrumMachine "AI Drum Machine" 1)
  add_ai_music_screenshot_exporter(AIBassSynth "AI Bass Synth" 2)
  add_ai_music_screenshot_exporter(AILeadSynth "AI Lead Synth" 4)
  add_ai_music_screenshot_exporter(AIPadSynth "AI Pad Synth" 5)
  add_ai_music_screenshot_exporter(AIPluckSynth "AI Pluck Synth" 6)
  add_ai_music_screenshot_exporter(AISampler "AI Sampler" 7)
  add_ai_music_screenshot_exporter(AIVEC1DrumPads "AI VEC1 Drum Pads" 10)
  add_ai_music_screenshot_exporter(AIPiano "AI Piano" 11)
  add_ai_music_screenshot_exporter(AIStrings "AI Strings" 12)
  add_ai_music_screenshot_exporter(AIViolin "AI Violin" 13)
  add_ai_music_screenshot_exporter(AIFlute "AI Flute" 14)
  add_ai_music_screenshot_exporter(AISaxophone "AI Saxophone" 15)
  add_ai_music_screenshot_exporter(AIBassGuitar "AI Bass Guitar" 16)
  add_ai_music_screenshot_exporter(AIOrgan "AI Organ" 17)
endif()

if(EXISTS "${AIMS_VEC1_EFFECTIVE_LIBRARY_DIR}")
  add_custom_command(TARGET AIVEC1DrumPads_VST3 POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E echo "Bundling VEC1 sample library into AI VEC1 Drum Pads.vst3"
    COMMAND ${CMAKE_COMMAND} -E rm -rf "$<TARGET_FILE_DIR:AIVEC1DrumPads_VST3>/../../Resources"
    COMMAND ${CMAKE_COMMAND} -E rm -rf "$<TARGET_FILE_DIR:AIVEC1DrumPads_VST3>/../Resources/VEC1"
    COMMAND ${CMAKE_COMMAND} -E copy_directory
            "${AIMS_VEC1_EFFECTIVE_LIBRARY_DIR}"
            "$<TARGET_FILE_DIR:AIVEC1DrumPads_VST3>/../Resources/VEC1"
    VERBATIM)
endif()

if(EXISTS "${AIMS_PIANO_EFFECTIVE_LIBRARY_DIR}")
  add_custom_command(TARGET AIPiano_VST3 POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E echo "Bundling Splendid Grand Piano into AI Piano.vst3"
    COMMAND ${CMAKE_COMMAND} -E rm -rf "$<TARGET_FILE_DIR:AIPiano_VST3>/../Resources/Piano"
    COMMAND ${CMAKE_COMMAND} -E copy_directory
            "${AIMS_PIANO_EFFECTIVE_LIBRARY_DIR}"
            "$<TARGET_FILE_DIR:AIPiano_VST3>/../Resources/Piano"
    VERBATIM)
endif()
