cmake_minimum_required(VERSION 3.22)

project(AdvancedVSTi VERSION 0.2.0)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Python3 COMPONENTS Interpreter QUIET)

if(NOT DEFINED JUCE_DIR)
  message(FATAL_ERROR "Set -DJUCE_DIR=/path/to/JUCE")
endif()

add_subdirectory(${JUCE_DIR} JUCE)

set(AIMS_REPO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}")
get_filename_component(AIMS_REPO_ROOT "${AIMS_REPO_ROOT}" ABSOLUTE)
set(AIMS_HOST_REPO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../..")
get_filename_component(AIMS_HOST_REPO_ROOT "${AIMS_HOST_REPO_ROOT}" ABSOLUTE)

set(AIMS_BINARY_DATA_PLACEHOLDER "${CMAKE_CURRENT_SOURCE_DIR}/Source/BinaryDataPlaceholder.txt")
set(AIMS_ASSET_SOURCES "${AIMS_BINARY_DATA_PLACEHOLDER}")
set(AIMS_HAS_TR909_IMAGE 0)
set(AIMS_VEC1_LIBRARY_DIR "D:/OneDrive/Music/Sound Design/Sample Library/sample library/VEC1")
set(AIMS_VVE1_LIBRARY_DIR "D:/OneDrive/Music/Sound Design/Sample Library/sample library/VVE1")
set(AIMS_PIANO_LIBRARY_DIR "${AIMS_REPO_ROOT}/.cache/SplendidGrandPiano")
if(NOT EXISTS "${AIMS_PIANO_LIBRARY_DIR}" AND EXISTS "${AIMS_HOST_REPO_ROOT}/.cache/SplendidGrandPiano")
  set(AIMS_PIANO_LIBRARY_DIR "${AIMS_HOST_REPO_ROOT}/.cache/SplendidGrandPiano")
endif()
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

function(bundle_ai_music_external_sample_library target_name library_id layout_name library_dir)
  if(NOT EXISTS "${library_dir}")
    return()
  endif()

  if(Python3_Interpreter_FOUND)
    add_custom_command(TARGET ${target_name}_VST3 POST_BUILD
      COMMAND ${CMAKE_COMMAND} -E echo "Bundling ${library_id} into ${target_name}.vst3 as a single sample pack"
      COMMAND ${CMAKE_COMMAND} -E make_directory "$<TARGET_FILE_DIR:${target_name}_VST3>/../Resources"
      COMMAND ${CMAKE_COMMAND} -E rm -f "$<TARGET_FILE_DIR:${target_name}_VST3>/../Resources/${library_id}.aimspack"
      COMMAND ${CMAKE_COMMAND} -E rm -rf "$<TARGET_FILE_DIR:${target_name}_VST3>/../Resources/${library_id}"
      COMMAND ${Python3_EXECUTABLE} "${AIMS_REPO_ROOT}/scripts/build_external_sample_pack.py"
              --layout ${layout_name}
              --library-root "${library_dir}"
              --library-id "${library_id}"
              --output "$<TARGET_FILE_DIR:${target_name}_VST3>/../Resources/${library_id}.aimspack"
      VERBATIM)
  else()
    message(WARNING "Python 3 was not found; ${library_id} will be bundled as a folder instead of a single sample pack.")
    add_custom_command(TARGET ${target_name}_VST3 POST_BUILD
      COMMAND ${CMAKE_COMMAND} -E echo "Bundling ${library_id} sample library into ${target_name}.vst3"
      COMMAND ${CMAKE_COMMAND} -E make_directory "$<TARGET_FILE_DIR:${target_name}_VST3>/../Resources"
      COMMAND ${CMAKE_COMMAND} -E rm -f "$<TARGET_FILE_DIR:${target_name}_VST3>/../Resources/${library_id}.aimspack"
      COMMAND ${CMAKE_COMMAND} -E rm -rf "$<TARGET_FILE_DIR:${target_name}_VST3>/../Resources/${library_id}"
      COMMAND ${CMAKE_COMMAND} -E copy_directory
              "${library_dir}"
              "$<TARGET_FILE_DIR:${target_name}_VST3>/../Resources/${library_id}"
      VERBATIM)
  endif()
endfunction()

add_ai_music_vst3(VirusSynth "Virus Synth" AdvS 0 com.aimusicstudio.virussynth)
add_ai_music_vst3(AIDrumMachine "AI Drum Machine" ADrm 1 com.aimusicstudio.aidrummachine)
add_ai_music_vst3(AIBassSynth "AI Bass Synth" ABas 2 com.aimusicstudio.aibasssynth)
add_ai_music_vst3(AIStringSynth "AI String Synth" AStr 3 com.aimusicstudio.aistringsynth)
add_ai_music_vst3(AILeadSynth "AI Lead Synth" ALed 4 com.aimusicstudio.aileadsynth)
add_ai_music_vst3(AIPadSynth "AI Pad Synth" APad 5 com.aimusicstudio.aipadsynth)
add_ai_music_vst3(AIPluckSynth "AI Pluck Synth" APlk 6 com.aimusicstudio.aiplucksynth)
add_ai_music_vst3(AISampler "AI Sampler" ASmp 7 com.aimusicstudio.aisampler)
add_ai_music_vst3(AI808Machine "AI 808 Machine" A808 8 com.aimusicstudio.ai808machine)
add_ai_music_vst3(AITB303 "AI TB303" ATB3 9 com.aimusicstudio.aitb303)
add_ai_music_vst3(AIVEC1DrumPads "AI VEC1 Drum Pads" AVPD 10 com.aimusicstudio.aivec1drumpads)
add_ai_music_vst3(AIPiano "AI Piano" AIPn 11 com.aimusicstudio.aipiano)
add_ai_music_vst3(AIStrings "AI Strings" AISe 12 com.aimusicstudio.aistrings)
add_ai_music_vst3(AIViolin "AI Violin" AIVl 13 com.aimusicstudio.aiviolin)
add_ai_music_vst3(AIFlute "AI Flute" AIFt 14 com.aimusicstudio.aiflute)
add_ai_music_vst3(AISaxophone "AI Saxophone" AISx 15 com.aimusicstudio.aisaxophone)
add_ai_music_vst3(AIBassGuitar "AI Bass Guitar" AIBG 16 com.aimusicstudio.aibassguitar)
add_ai_music_vst3(AIOrgan "AI Organ" AIOr 17 com.aimusicstudio.aiorgan)
add_ai_music_vst3(AIVVE1VocalMachine "AI VVE1 Vocal Machine" AVVM 18 com.aimusicstudio.aivve1vocalmachine)

if(AIMS_BUILD_SCREENSHOT_EXPORTERS)
  add_ai_music_screenshot_exporter(VirusSynth "Virus Synth" 0)
  add_ai_music_screenshot_exporter(AIDrumMachine "AI Drum Machine" 1)
  add_ai_music_screenshot_exporter(AIBassSynth "AI Bass Synth" 2)
  add_ai_music_screenshot_exporter(AIStringSynth "AI String Synth" 3)
  add_ai_music_screenshot_exporter(AILeadSynth "AI Lead Synth" 4)
  add_ai_music_screenshot_exporter(AIPadSynth "AI Pad Synth" 5)
  add_ai_music_screenshot_exporter(AIPluckSynth "AI Pluck Synth" 6)
  add_ai_music_screenshot_exporter(AISampler "AI Sampler" 7)
  add_ai_music_screenshot_exporter(AI808Machine "AI 808 Machine" 8)
  add_ai_music_screenshot_exporter(AITB303 "AI TB303" 9)
  add_ai_music_screenshot_exporter(AIVEC1DrumPads "AI VEC1 Drum Pads" 10)
  add_ai_music_screenshot_exporter(AIPiano "AI Piano" 11)
  add_ai_music_screenshot_exporter(AIStrings "AI Strings" 12)
  add_ai_music_screenshot_exporter(AIViolin "AI Violin" 13)
  add_ai_music_screenshot_exporter(AIFlute "AI Flute" 14)
  add_ai_music_screenshot_exporter(AISaxophone "AI Saxophone" 15)
  add_ai_music_screenshot_exporter(AIBassGuitar "AI Bass Guitar" 16)
  add_ai_music_screenshot_exporter(AIOrgan "AI Organ" 17)
  add_ai_music_screenshot_exporter(AIVVE1VocalMachine "AI VVE1 Vocal Machine" 18)
endif()

bundle_ai_music_external_sample_library(AIVEC1DrumPads VEC1 vec1 "${AIMS_VEC1_LIBRARY_DIR}")
bundle_ai_music_external_sample_library(AIVVE1VocalMachine VVE1 vve1 "${AIMS_VVE1_LIBRARY_DIR}")

if(EXISTS "${AIMS_PIANO_LIBRARY_DIR}")
  add_custom_command(TARGET AIPiano_VST3 POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E echo "Bundling Splendid Grand Piano into AI Piano.vst3"
    COMMAND ${CMAKE_COMMAND} -E rm -rf "$<TARGET_FILE_DIR:AIPiano_VST3>/../Resources/Piano"
    COMMAND ${CMAKE_COMMAND} -E copy_directory
            "${AIMS_PIANO_LIBRARY_DIR}"
            "$<TARGET_FILE_DIR:AIPiano_VST3>/../Resources/Piano"
    VERBATIM)
endif()
