#include <JuceHeader.h>
#include <iostream>
#include <memory>
#include "../Source/PluginEditor.h"
#include "../Source/PluginProcessor.h"

namespace
{
juce::File resolveOutputPath (int argc, char* argv[])
{
    if (argc < 2)
        return {};

    return juce::File::getCurrentWorkingDirectory().getChildFile (juce::String::fromUTF8 (argv[1]));
}

bool writePng (const juce::Image& image, const juce::File& outputFile)
{
    if (! image.isValid())
        return false;

    outputFile.getParentDirectory().createDirectory();
    juce::FileOutputStream output (outputFile);

    if (! output.openedOk())
        return false;

    juce::PNGImageFormat pngFormat;
    return pngFormat.writeImageToStream (image, output);
}
}

int main (int argc, char* argv[])
{
    const auto outputFile = resolveOutputPath (argc, argv);
    if (outputFile == juce::File())
    {
        std::cerr << "Usage: ScreenshotExporter <output-png-path>\n";
        return 1;
    }

    juce::ScopedJuceInitialiser_GUI gui;

    AdvancedVSTiAudioProcessor processor;
    processor.prepareToPlay (44100.0, 512);

    auto editor = std::unique_ptr<juce::AudioProcessorEditor> (processor.createEditor());
    if (editor == nullptr)
    {
        std::cerr << "Failed to create editor.\n";
        return 2;
    }

    editor->setVisible (true);
    editor->resized();

    const auto snapshot = editor->createComponentSnapshot (editor->getLocalBounds(), true, 1.0f);
    if (! writePng (snapshot, outputFile))
    {
        std::cerr << "Failed to write screenshot to " << outputFile.getFullPathName() << "\n";
        return 3;
    }

    std::cout << "Wrote screenshot to " << outputFile.getFullPathName() << "\n";
    return 0;
}
