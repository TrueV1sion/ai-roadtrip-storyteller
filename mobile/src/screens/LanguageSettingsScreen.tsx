import React, { useState, useEffect } from 'react';
import { View, StyleSheet, FlatList } from 'react-native';
import { Text, List, Surface, Button, RadioButton, Divider } from 'react-native-paper';
import { MaterialIcons } from '@expo/vector-icons';

import { COLORS, SPACING } from '../theme';
import { useTranslation } from '../i18n';

const LanguageSettingsScreen: React.FC = () => {
  const { locales, localeName, setLocale, locale: currentLocale, t } = useTranslation();
  const [selectedLocale, setSelectedLocale] = useState(currentLocale);
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    setHasChanges(selectedLocale !== currentLocale);
  }, [selectedLocale, currentLocale]);

  const handleLocaleChange = (locale: string) => {
    setSelectedLocale(locale);
  };

  const applyChanges = async () => {
    await setLocale(selectedLocale);
    // Navigate back or show confirmation
  };

  return (
    <View style={styles.container}>
      <Surface style={styles.languageSelector}>
        <Text style={styles.title}>{t('language.select')}</Text>
        <Text style={styles.subtitle}>{t('language.subtitle')}</Text>
        
        <RadioButton.Group onValueChange={handleLocaleChange} value={selectedLocale}>
          <FlatList
            data={locales}
            keyExtractor={(item) => item}
            renderItem={({ item }) => (
              <List.Item
                title={localeName(item)}
                description={item === currentLocale ? t('common.current') : ''}
                onPress={() => handleLocaleChange(item)}
                left={props => (
                  <RadioButton 
                    {...props} 
                    value={item} 
                    color={COLORS.primary}
                    accessibilityLabel={`${localeName(item)} ${t('language.option')}`}
                  />
                )}
                right={props => 
                  item === selectedLocale ? (
                    <MaterialIcons 
                      name="check" 
                      size={24} 
                      color={COLORS.primary} 
                      style={props.style} 
                    />
                  ) : null
                }
                accessibilityHint={t('language.hint')}
              />
            )}
            ItemSeparatorComponent={() => <Divider />}
            contentContainerStyle={styles.listContent}
          />
        </RadioButton.Group>
      </Surface>
      
      <View style={styles.noteContainer}>
        <MaterialIcons name="info" size={20} color={COLORS.textSecondary} />
        <Text style={styles.note}>
          {t('language.note')}
        </Text>
      </View>
      
      <Button
        mode="contained"
        onPress={applyChanges}
        style={styles.applyButton}
        disabled={!hasChanges}
        accessibilityLabel={t('common.apply')}
      >
        {t('common.apply')}
      </Button>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: SPACING.medium,
    backgroundColor: COLORS.background,
  },
  languageSelector: {
    padding: SPACING.medium,
    borderRadius: 8,
  },
  title: {
    fontSize: 20,
    fontWeight: 'bold',
    marginBottom: SPACING.small,
  },
  subtitle: {
    fontSize: 14,
    color: COLORS.textSecondary,
    marginBottom: SPACING.medium,
  },
  listContent: {
    paddingBottom: SPACING.medium,
  },
  separator: {
    height: 1,
    backgroundColor: COLORS.border,
  },
  noteContainer: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginTop: SPACING.large,
    padding: SPACING.medium,
  },
  note: {
    fontSize: 14,
    color: COLORS.textSecondary,
    marginLeft: SPACING.small,
    flex: 1,
  },
  applyButton: {
    marginTop: SPACING.large,
  },
});

export default LanguageSettingsScreen; 