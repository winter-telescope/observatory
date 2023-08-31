/********************************************************************************
** Form generated from reading UI file 'PStyleChooser.ui'
**
** Created by: Qt User Interface Compiler version 5.9.7
**
** WARNING! All changes made in this file will be lost when recompiling UI file!
********************************************************************************/

#ifndef UI_PSTYLECHOOSER_H
#define UI_PSTYLECHOOSER_H

#include <QtCore/QVariant>
#include <QtWidgets/QAction>
#include <QtWidgets/QApplication>
#include <QtWidgets/QButtonGroup>
#include <QtWidgets/QComboBox>
#include <QtWidgets/QHBoxLayout>
#include <QtWidgets/QHeaderView>
#include <QtWidgets/QToolButton>
#include <QtWidgets/QWidget>

QT_BEGIN_NAMESPACE

class Ui_PStyleChooser
{
public:
    QHBoxLayout *horizontalLayout;
    QComboBox *comboBoxStyle;
    QToolButton *toolButtonFG;
    QToolButton *toolButtonBG;
    QToolButton *toolButtonB;
    QToolButton *toolButtonI;

    void setupUi(QWidget *PStyleChooser)
    {
        if (PStyleChooser->objectName().isEmpty())
            PStyleChooser->setObjectName(QStringLiteral("PStyleChooser"));
        PStyleChooser->resize(195, 32);
        QSizePolicy sizePolicy(QSizePolicy::Preferred, QSizePolicy::Fixed);
        sizePolicy.setHorizontalStretch(0);
        sizePolicy.setVerticalStretch(0);
        sizePolicy.setHeightForWidth(PStyleChooser->sizePolicy().hasHeightForWidth());
        PStyleChooser->setSizePolicy(sizePolicy);
        horizontalLayout = new QHBoxLayout(PStyleChooser);
        horizontalLayout->setObjectName(QStringLiteral("horizontalLayout"));
        comboBoxStyle = new QComboBox(PStyleChooser);
        comboBoxStyle->setObjectName(QStringLiteral("comboBoxStyle"));
        comboBoxStyle->setMinimumSize(QSize(0, 22));
        QFont font;
        font.setPointSize(7);
        comboBoxStyle->setFont(font);

        horizontalLayout->addWidget(comboBoxStyle);

        toolButtonFG = new QToolButton(PStyleChooser);
        toolButtonFG->setObjectName(QStringLiteral("toolButtonFG"));
        toolButtonFG->setEnabled(false);
        toolButtonFG->setMinimumSize(QSize(0, 22));
        toolButtonFG->setFont(font);

        horizontalLayout->addWidget(toolButtonFG);

        toolButtonBG = new QToolButton(PStyleChooser);
        toolButtonBG->setObjectName(QStringLiteral("toolButtonBG"));
        toolButtonBG->setEnabled(false);
        toolButtonBG->setMinimumSize(QSize(0, 22));
        toolButtonBG->setFont(font);

        horizontalLayout->addWidget(toolButtonBG);

        toolButtonB = new QToolButton(PStyleChooser);
        toolButtonB->setObjectName(QStringLiteral("toolButtonB"));
        toolButtonB->setEnabled(false);
        toolButtonB->setMinimumSize(QSize(0, 22));
        QFont font1;
        font1.setPointSize(7);
        font1.setBold(true);
        font1.setWeight(75);
        toolButtonB->setFont(font1);
        toolButtonB->setCheckable(true);

        horizontalLayout->addWidget(toolButtonB);

        toolButtonI = new QToolButton(PStyleChooser);
        toolButtonI->setObjectName(QStringLiteral("toolButtonI"));
        toolButtonI->setEnabled(false);
        toolButtonI->setMinimumSize(QSize(0, 22));
        QFont font2;
        font2.setPointSize(7);
        font2.setItalic(true);
        toolButtonI->setFont(font2);
        toolButtonI->setCheckable(true);

        horizontalLayout->addWidget(toolButtonI);


        retranslateUi(PStyleChooser);

        QMetaObject::connectSlotsByName(PStyleChooser);
    } // setupUi

    void retranslateUi(QWidget *PStyleChooser)
    {
        PStyleChooser->setWindowTitle(QApplication::translate("PStyleChooser", "Form", Q_NULLPTR));
        comboBoxStyle->clear();
        comboBoxStyle->insertItems(0, QStringList()
         << QApplication::translate("PStyleChooser", "No Style", Q_NULLPTR)
         << QApplication::translate("PStyleChooser", "New Style", Q_NULLPTR)
        );
        toolButtonFG->setText(QApplication::translate("PStyleChooser", "f", Q_NULLPTR));
        toolButtonBG->setText(QApplication::translate("PStyleChooser", "b", Q_NULLPTR));
        toolButtonB->setText(QApplication::translate("PStyleChooser", "B", Q_NULLPTR));
        toolButtonI->setText(QApplication::translate("PStyleChooser", "i", Q_NULLPTR));
    } // retranslateUi

};

namespace Ui {
    class PStyleChooser: public Ui_PStyleChooser {};
} // namespace Ui

QT_END_NAMESPACE

#endif // UI_PSTYLECHOOSER_H
