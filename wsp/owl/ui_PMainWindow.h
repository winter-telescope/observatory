/********************************************************************************
** Form generated from reading UI file 'PMainWindow.ui'
**
** Created by: Qt User Interface Compiler version 5.9.7
**
** WARNING! All changes made in this file will be lost when recompiling UI file!
********************************************************************************/

#ifndef UI_PMAINWINDOW_H
#define UI_PMAINWINDOW_H

#include <QtCore/QVariant>
#include <QtWidgets/QAction>
#include <QtWidgets/QApplication>
#include <QtWidgets/QButtonGroup>
#include <QtWidgets/QCheckBox>
#include <QtWidgets/QComboBox>
#include <QtWidgets/QDockWidget>
#include <QtWidgets/QDoubleSpinBox>
#include <QtWidgets/QFormLayout>
#include <QtWidgets/QGridLayout>
#include <QtWidgets/QHBoxLayout>
#include <QtWidgets/QHeaderView>
#include <QtWidgets/QLabel>
#include <QtWidgets/QLineEdit>
#include <QtWidgets/QListWidget>
#include <QtWidgets/QMainWindow>
#include <QtWidgets/QPushButton>
#include <QtWidgets/QRadioButton>
#include <QtWidgets/QScrollArea>
#include <QtWidgets/QSpacerItem>
#include <QtWidgets/QSpinBox>
#include <QtWidgets/QStatusBar>
#include <QtWidgets/QTableWidget>
#include <QtWidgets/QToolBar>
#include <QtWidgets/QVBoxLayout>
#include <QtWidgets/QWidget>
#include "PStyleChooser.h"

QT_BEGIN_NAMESPACE

class Ui_PMainWindow
{
public:
    QAction *actionConfigure;
    QAction *actionLink;
    QAction *actionSave;
    QAction *actionSaveAs;
    QAction *actionLoad;
    QAction *actionHelp;
    QAction *actionReset;
    QAction *actionServer_Options;
    QWidget *centralwidget;
    QGridLayout *gridLayout;
    QStatusBar *statusbar;
    QDockWidget *dockConfigure;
    QWidget *dockWidgetContents_2;
    QVBoxLayout *verticalLayout;
    QLabel *label;
    QListWidget *listWidgetInsertReal;
    QLabel *label_2;
    QScrollArea *scrollArea;
    QWidget *scrollAreaWidgetContents_4;
    QGridLayout *gridLayout_2;
    QLineEdit *lineEditHighWord;
    QHBoxLayout *horizontalLayout_4;
    QDoubleSpinBox *doubleSpinBoxXHigh;
    QDoubleSpinBox *doubleSpinBoxHigh;
    QDoubleSpinBox *doubleSpinBoxXLow;
    QLabel *labelSource;
    QSpacerItem *verticalSpacerConfigure;
    QSpinBox *spinBoxNBits;
    QLabel *labelNBits;
    QLabel *labelHighWord;
    QLineEdit *lineEditExtremaName;
    QLabel *labelFormat_num;
    QComboBox *comboBox;
    PStyleChooser *pstyleHigh;
    QLabel *labelType;
    QLabel *labelCurRow;
    QLineEdit *lineEditFormat;
    QLabel *labelExtrema;
    QHBoxLayout *horizontalLayout_2;
    QPushButton *pushButtonAddFormat;
    QPushButton *pushButtonDelFormat;
    QLabel *labelHigh;
    QDoubleSpinBox *doubleSpinBoxLow;
    QLineEdit *lineEditSource;
    PStyleChooser *pstyleLow;
    QLabel *labelFormat_multi;
    QComboBox *comboBoxExtrema;
    QLabel *labelXLow;
    QLineEdit *lineEditCaption;
    QComboBox *comboBoxType;
    PStyleChooser *pstyleCaption;
    QLabel *labelCaption;
    QLabel *labelXHigh;
    PStyleChooser *pstyleXHigh;
    PStyleChooser *pstyleData;
    PStyleChooser *pstyleXLow;
    QLabel *labelLow;
    QLabel *labelName;
    QTableWidget *tableWidgetFormat;
    PStyleChooser *pstyleSelected;
    QPushButton *pushButtonRemove;
    QLabel *labelLowWord;
    QLineEdit *lineEditLowWord;
    QToolBar *toolBar;
    QDockWidget *dockLink;
    QWidget *dockWidgetContents_4;
    QGridLayout *gridLayout_3;
    QLineEdit *lineEditIridium;
    QRadioButton *radioButtonHighGain;
    QRadioButton *radioButtonLOS;
    QLineEdit *lineEditLOS;
    QRadioButton *radioButtonTDRSSOmni;
    QLineEdit *lineEditTDRSSOmni;
    QRadioButton *radioButtonIridium;
    QLineEdit *lineEditHighGain;
    QRadioButton *radioButtonLoRate;
    QLineEdit *lineEditLoRate;
    QPushButton *pushButtonResetLink;
    QSpacerItem *verticalSpacer_2;
    QDockWidget *dockWebServer;
    QWidget *dockWebServerLayout;
    QFormLayout *formLayout;
    QSpacerItem *verticalSpacer;
    QSpinBox *spinBoxServerPort;
    QCheckBox *checkBoxServer;

    void setupUi(QMainWindow *PMainWindow)
    {
        if (PMainWindow->objectName().isEmpty())
            PMainWindow->setObjectName(QStringLiteral("PMainWindow"));
        PMainWindow->resize(714, 1084);
        actionConfigure = new QAction(PMainWindow);
        actionConfigure->setObjectName(QStringLiteral("actionConfigure"));
        actionConfigure->setCheckable(true);
        QIcon icon;
        icon.addFile(QStringLiteral(":/icons/icons/document-edit.png"), QSize(), QIcon::Normal, QIcon::Off);
        actionConfigure->setIcon(icon);
        actionLink = new QAction(PMainWindow);
        actionLink->setObjectName(QStringLiteral("actionLink"));
        actionLink->setCheckable(true);
        QIcon icon1;
        icon1.addFile(QStringLiteral(":/icons/icons/link.png"), QSize(), QIcon::Normal, QIcon::Off);
        actionLink->setIcon(icon1);
        actionSave = new QAction(PMainWindow);
        actionSave->setObjectName(QStringLiteral("actionSave"));
        QIcon icon2;
        icon2.addFile(QStringLiteral(":/icons/icons/document-save.png"), QSize(), QIcon::Normal, QIcon::Off);
        actionSave->setIcon(icon2);
        actionSaveAs = new QAction(PMainWindow);
        actionSaveAs->setObjectName(QStringLiteral("actionSaveAs"));
        QIcon icon3;
        icon3.addFile(QStringLiteral(":/icons/icons/document-save-as.png"), QSize(), QIcon::Normal, QIcon::Off);
        actionSaveAs->setIcon(icon3);
        actionLoad = new QAction(PMainWindow);
        actionLoad->setObjectName(QStringLiteral("actionLoad"));
        QIcon icon4;
        icon4.addFile(QStringLiteral(":/icons/icons/document-open.png"), QSize(), QIcon::Normal, QIcon::Off);
        actionLoad->setIcon(icon4);
        actionHelp = new QAction(PMainWindow);
        actionHelp->setObjectName(QStringLiteral("actionHelp"));
        actionReset = new QAction(PMainWindow);
        actionReset->setObjectName(QStringLiteral("actionReset"));
        QIcon icon5;
        icon5.addFile(QStringLiteral(":/icons/icons/view-refresh.png"), QSize(), QIcon::Normal, QIcon::Off);
        actionReset->setIcon(icon5);
        actionServer_Options = new QAction(PMainWindow);
        actionServer_Options->setObjectName(QStringLiteral("actionServer_Options"));
        actionServer_Options->setCheckable(true);
        QIcon icon6;
        icon6.addFile(QStringLiteral(":/icons/icons/server.png"), QSize(), QIcon::Normal, QIcon::Off);
        actionServer_Options->setIcon(icon6);
        centralwidget = new QWidget(PMainWindow);
        centralwidget->setObjectName(QStringLiteral("centralwidget"));
        gridLayout = new QGridLayout(centralwidget);
        gridLayout->setObjectName(QStringLiteral("gridLayout"));
        PMainWindow->setCentralWidget(centralwidget);
        statusbar = new QStatusBar(PMainWindow);
        statusbar->setObjectName(QStringLiteral("statusbar"));
        PMainWindow->setStatusBar(statusbar);
        dockConfigure = new QDockWidget(PMainWindow);
        dockConfigure->setObjectName(QStringLiteral("dockConfigure"));
        dockConfigure->setMinimumSize(QSize(112, 688));
        dockWidgetContents_2 = new QWidget();
        dockWidgetContents_2->setObjectName(QStringLiteral("dockWidgetContents_2"));
        verticalLayout = new QVBoxLayout(dockWidgetContents_2);
        verticalLayout->setObjectName(QStringLiteral("verticalLayout"));
        label = new QLabel(dockWidgetContents_2);
        label->setObjectName(QStringLiteral("label"));
        QSizePolicy sizePolicy(QSizePolicy::Preferred, QSizePolicy::Fixed);
        sizePolicy.setHorizontalStretch(0);
        sizePolicy.setVerticalStretch(0);
        sizePolicy.setHeightForWidth(label->sizePolicy().hasHeightForWidth());
        label->setSizePolicy(sizePolicy);

        verticalLayout->addWidget(label);

        listWidgetInsertReal = new QListWidget(dockWidgetContents_2);
        new QListWidgetItem(listWidgetInsertReal);
        new QListWidgetItem(listWidgetInsertReal);
        new QListWidgetItem(listWidgetInsertReal);
        new QListWidgetItem(listWidgetInsertReal);
        new QListWidgetItem(listWidgetInsertReal);
        new QListWidgetItem(listWidgetInsertReal);
        new QListWidgetItem(listWidgetInsertReal);
        listWidgetInsertReal->setObjectName(QStringLiteral("listWidgetInsertReal"));
        QSizePolicy sizePolicy1(QSizePolicy::Expanding, QSizePolicy::Fixed);
        sizePolicy1.setHorizontalStretch(0);
        sizePolicy1.setVerticalStretch(0);
        sizePolicy1.setHeightForWidth(listWidgetInsertReal->sizePolicy().hasHeightForWidth());
        listWidgetInsertReal->setSizePolicy(sizePolicy1);
        listWidgetInsertReal->setDragEnabled(true);

        verticalLayout->addWidget(listWidgetInsertReal);

        label_2 = new QLabel(dockWidgetContents_2);
        label_2->setObjectName(QStringLiteral("label_2"));
        sizePolicy.setHeightForWidth(label_2->sizePolicy().hasHeightForWidth());
        label_2->setSizePolicy(sizePolicy);

        verticalLayout->addWidget(label_2);

        scrollArea = new QScrollArea(dockWidgetContents_2);
        scrollArea->setObjectName(QStringLiteral("scrollArea"));
        QSizePolicy sizePolicy2(QSizePolicy::Expanding, QSizePolicy::MinimumExpanding);
        sizePolicy2.setHorizontalStretch(0);
        sizePolicy2.setVerticalStretch(0);
        sizePolicy2.setHeightForWidth(scrollArea->sizePolicy().hasHeightForWidth());
        scrollArea->setSizePolicy(sizePolicy2);
        scrollArea->setFrameShape(QFrame::NoFrame);
        scrollArea->setFrameShadow(QFrame::Plain);
        scrollArea->setWidgetResizable(true);
        scrollAreaWidgetContents_4 = new QWidget();
        scrollAreaWidgetContents_4->setObjectName(QStringLiteral("scrollAreaWidgetContents_4"));
        scrollAreaWidgetContents_4->setGeometry(QRect(0, 0, 440, 810));
        gridLayout_2 = new QGridLayout(scrollAreaWidgetContents_4);
        gridLayout_2->setObjectName(QStringLiteral("gridLayout_2"));
        lineEditHighWord = new QLineEdit(scrollAreaWidgetContents_4);
        lineEditHighWord->setObjectName(QStringLiteral("lineEditHighWord"));

        gridLayout_2->addWidget(lineEditHighWord, 8, 1, 1, 1);

        horizontalLayout_4 = new QHBoxLayout();
        horizontalLayout_4->setObjectName(QStringLiteral("horizontalLayout_4"));
        doubleSpinBoxXHigh = new QDoubleSpinBox(scrollAreaWidgetContents_4);
        doubleSpinBoxXHigh->setObjectName(QStringLiteral("doubleSpinBoxXHigh"));
        sizePolicy1.setHeightForWidth(doubleSpinBoxXHigh->sizePolicy().hasHeightForWidth());
        doubleSpinBoxXHigh->setSizePolicy(sizePolicy1);
        doubleSpinBoxXHigh->setDecimals(10);
        doubleSpinBoxXHigh->setMinimum(-1e+9);
        doubleSpinBoxXHigh->setMaximum(1e+9);

        horizontalLayout_4->addWidget(doubleSpinBoxXHigh);


        gridLayout_2->addLayout(horizontalLayout_4, 15, 1, 1, 1);

        doubleSpinBoxHigh = new QDoubleSpinBox(scrollAreaWidgetContents_4);
        doubleSpinBoxHigh->setObjectName(QStringLiteral("doubleSpinBoxHigh"));
        sizePolicy1.setHeightForWidth(doubleSpinBoxHigh->sizePolicy().hasHeightForWidth());
        doubleSpinBoxHigh->setSizePolicy(sizePolicy1);
        doubleSpinBoxHigh->setDecimals(10);
        doubleSpinBoxHigh->setMinimum(-1e+9);
        doubleSpinBoxHigh->setMaximum(1e+9);

        gridLayout_2->addWidget(doubleSpinBoxHigh, 17, 1, 1, 1);

        doubleSpinBoxXLow = new QDoubleSpinBox(scrollAreaWidgetContents_4);
        doubleSpinBoxXLow->setObjectName(QStringLiteral("doubleSpinBoxXLow"));
        sizePolicy1.setHeightForWidth(doubleSpinBoxXLow->sizePolicy().hasHeightForWidth());
        doubleSpinBoxXLow->setSizePolicy(sizePolicy1);
        doubleSpinBoxXLow->setDecimals(10);
        doubleSpinBoxXLow->setMinimum(-1e+9);
        doubleSpinBoxXLow->setMaximum(1e+9);

        gridLayout_2->addWidget(doubleSpinBoxXLow, 21, 1, 1, 1);

        labelSource = new QLabel(scrollAreaWidgetContents_4);
        labelSource->setObjectName(QStringLiteral("labelSource"));
        QFont font;
        font.setBold(true);
        font.setUnderline(true);
        font.setWeight(75);
        labelSource->setFont(font);
        labelSource->setAlignment(Qt::AlignRight|Qt::AlignTrailing|Qt::AlignVCenter);

        gridLayout_2->addWidget(labelSource, 3, 0, 1, 1);

        verticalSpacerConfigure = new QSpacerItem(14, 42, QSizePolicy::Minimum, QSizePolicy::Expanding);

        gridLayout_2->addItem(verticalSpacerConfigure, 24, 1, 1, 1);

        spinBoxNBits = new QSpinBox(scrollAreaWidgetContents_4);
        spinBoxNBits->setObjectName(QStringLiteral("spinBoxNBits"));
        spinBoxNBits->setMaximum(32);

        gridLayout_2->addWidget(spinBoxNBits, 7, 1, 1, 1);

        labelNBits = new QLabel(scrollAreaWidgetContents_4);
        labelNBits->setObjectName(QStringLiteral("labelNBits"));

        gridLayout_2->addWidget(labelNBits, 7, 0, 1, 1);

        labelHighWord = new QLabel(scrollAreaWidgetContents_4);
        labelHighWord->setObjectName(QStringLiteral("labelHighWord"));

        gridLayout_2->addWidget(labelHighWord, 8, 0, 1, 1);

        lineEditExtremaName = new QLineEdit(scrollAreaWidgetContents_4);
        lineEditExtremaName->setObjectName(QStringLiteral("lineEditExtremaName"));

        gridLayout_2->addWidget(lineEditExtremaName, 14, 1, 1, 1);

        labelFormat_num = new QLabel(scrollAreaWidgetContents_4);
        labelFormat_num->setObjectName(QStringLiteral("labelFormat_num"));
        labelFormat_num->setAlignment(Qt::AlignRight|Qt::AlignTrailing|Qt::AlignVCenter);

        gridLayout_2->addWidget(labelFormat_num, 6, 0, 1, 1);

        comboBox = new QComboBox(scrollAreaWidgetContents_4);
        comboBox->setObjectName(QStringLiteral("comboBox"));

        gridLayout_2->addWidget(comboBox, 0, 0, 1, 2);

        pstyleHigh = new PStyleChooser(scrollAreaWidgetContents_4);
        pstyleHigh->setObjectName(QStringLiteral("pstyleHigh"));
        QSizePolicy sizePolicy3(QSizePolicy::Expanding, QSizePolicy::Preferred);
        sizePolicy3.setHorizontalStretch(0);
        sizePolicy3.setVerticalStretch(0);
        sizePolicy3.setHeightForWidth(pstyleHigh->sizePolicy().hasHeightForWidth());
        pstyleHigh->setSizePolicy(sizePolicy3);
        pstyleHigh->setMinimumSize(QSize(0, 26));

        gridLayout_2->addWidget(pstyleHigh, 18, 0, 1, 2);

        labelType = new QLabel(scrollAreaWidgetContents_4);
        labelType->setObjectName(QStringLiteral("labelType"));
        labelType->setFont(font);
        labelType->setAlignment(Qt::AlignRight|Qt::AlignTrailing|Qt::AlignVCenter);

        gridLayout_2->addWidget(labelType, 5, 0, 1, 1);

        labelCurRow = new QLabel(scrollAreaWidgetContents_4);
        labelCurRow->setObjectName(QStringLiteral("labelCurRow"));
        labelCurRow->setAlignment(Qt::AlignRight|Qt::AlignTrailing|Qt::AlignVCenter);

        gridLayout_2->addWidget(labelCurRow, 12, 0, 1, 1);

        lineEditFormat = new QLineEdit(scrollAreaWidgetContents_4);
        lineEditFormat->setObjectName(QStringLiteral("lineEditFormat"));

        gridLayout_2->addWidget(lineEditFormat, 6, 1, 1, 1);

        labelExtrema = new QLabel(scrollAreaWidgetContents_4);
        labelExtrema->setObjectName(QStringLiteral("labelExtrema"));
        labelExtrema->setFont(font);

        gridLayout_2->addWidget(labelExtrema, 13, 0, 1, 1);

        horizontalLayout_2 = new QHBoxLayout();
        horizontalLayout_2->setObjectName(QStringLiteral("horizontalLayout_2"));
        pushButtonAddFormat = new QPushButton(scrollAreaWidgetContents_4);
        pushButtonAddFormat->setObjectName(QStringLiteral("pushButtonAddFormat"));
        sizePolicy1.setHeightForWidth(pushButtonAddFormat->sizePolicy().hasHeightForWidth());
        pushButtonAddFormat->setSizePolicy(sizePolicy1);

        horizontalLayout_2->addWidget(pushButtonAddFormat);

        pushButtonDelFormat = new QPushButton(scrollAreaWidgetContents_4);
        pushButtonDelFormat->setObjectName(QStringLiteral("pushButtonDelFormat"));
        sizePolicy1.setHeightForWidth(pushButtonDelFormat->sizePolicy().hasHeightForWidth());
        pushButtonDelFormat->setSizePolicy(sizePolicy1);

        horizontalLayout_2->addWidget(pushButtonDelFormat);


        gridLayout_2->addLayout(horizontalLayout_2, 11, 1, 1, 1);

        labelHigh = new QLabel(scrollAreaWidgetContents_4);
        labelHigh->setObjectName(QStringLiteral("labelHigh"));
        labelHigh->setAlignment(Qt::AlignRight|Qt::AlignTrailing|Qt::AlignVCenter);

        gridLayout_2->addWidget(labelHigh, 17, 0, 1, 1);

        doubleSpinBoxLow = new QDoubleSpinBox(scrollAreaWidgetContents_4);
        doubleSpinBoxLow->setObjectName(QStringLiteral("doubleSpinBoxLow"));
        sizePolicy1.setHeightForWidth(doubleSpinBoxLow->sizePolicy().hasHeightForWidth());
        doubleSpinBoxLow->setSizePolicy(sizePolicy1);
        doubleSpinBoxLow->setDecimals(10);
        doubleSpinBoxLow->setMinimum(-1e+9);
        doubleSpinBoxLow->setMaximum(1e+9);

        gridLayout_2->addWidget(doubleSpinBoxLow, 19, 1, 1, 1);

        lineEditSource = new QLineEdit(scrollAreaWidgetContents_4);
        lineEditSource->setObjectName(QStringLiteral("lineEditSource"));

        gridLayout_2->addWidget(lineEditSource, 3, 1, 1, 1);

        pstyleLow = new PStyleChooser(scrollAreaWidgetContents_4);
        pstyleLow->setObjectName(QStringLiteral("pstyleLow"));
        sizePolicy3.setHeightForWidth(pstyleLow->sizePolicy().hasHeightForWidth());
        pstyleLow->setSizePolicy(sizePolicy3);
        pstyleLow->setMinimumSize(QSize(0, 26));

        gridLayout_2->addWidget(pstyleLow, 20, 0, 1, 2);

        labelFormat_multi = new QLabel(scrollAreaWidgetContents_4);
        labelFormat_multi->setObjectName(QStringLiteral("labelFormat_multi"));
        labelFormat_multi->setAlignment(Qt::AlignRight|Qt::AlignTrailing|Qt::AlignVCenter);

        gridLayout_2->addWidget(labelFormat_multi, 10, 0, 1, 1);

        comboBoxExtrema = new QComboBox(scrollAreaWidgetContents_4);
        comboBoxExtrema->setObjectName(QStringLiteral("comboBoxExtrema"));
        sizePolicy1.setHeightForWidth(comboBoxExtrema->sizePolicy().hasHeightForWidth());
        comboBoxExtrema->setSizePolicy(sizePolicy1);

        gridLayout_2->addWidget(comboBoxExtrema, 13, 1, 1, 1);

        labelXLow = new QLabel(scrollAreaWidgetContents_4);
        labelXLow->setObjectName(QStringLiteral("labelXLow"));
        labelXLow->setAlignment(Qt::AlignRight|Qt::AlignTrailing|Qt::AlignVCenter);

        gridLayout_2->addWidget(labelXLow, 21, 0, 1, 1);

        lineEditCaption = new QLineEdit(scrollAreaWidgetContents_4);
        lineEditCaption->setObjectName(QStringLiteral("lineEditCaption"));

        gridLayout_2->addWidget(lineEditCaption, 1, 1, 1, 1);

        comboBoxType = new QComboBox(scrollAreaWidgetContents_4);
        comboBoxType->setObjectName(QStringLiteral("comboBoxType"));
        sizePolicy1.setHeightForWidth(comboBoxType->sizePolicy().hasHeightForWidth());
        comboBoxType->setSizePolicy(sizePolicy1);

        gridLayout_2->addWidget(comboBoxType, 5, 1, 1, 1);

        pstyleCaption = new PStyleChooser(scrollAreaWidgetContents_4);
        pstyleCaption->setObjectName(QStringLiteral("pstyleCaption"));
        sizePolicy3.setHeightForWidth(pstyleCaption->sizePolicy().hasHeightForWidth());
        pstyleCaption->setSizePolicy(sizePolicy3);
        pstyleCaption->setMinimumSize(QSize(0, 26));

        gridLayout_2->addWidget(pstyleCaption, 2, 0, 1, 2);

        labelCaption = new QLabel(scrollAreaWidgetContents_4);
        labelCaption->setObjectName(QStringLiteral("labelCaption"));
        labelCaption->setFont(font);
        labelCaption->setAlignment(Qt::AlignRight|Qt::AlignTrailing|Qt::AlignVCenter);

        gridLayout_2->addWidget(labelCaption, 1, 0, 1, 1);

        labelXHigh = new QLabel(scrollAreaWidgetContents_4);
        labelXHigh->setObjectName(QStringLiteral("labelXHigh"));
        labelXHigh->setAlignment(Qt::AlignRight|Qt::AlignTrailing|Qt::AlignVCenter);

        gridLayout_2->addWidget(labelXHigh, 15, 0, 1, 1);

        pstyleXHigh = new PStyleChooser(scrollAreaWidgetContents_4);
        pstyleXHigh->setObjectName(QStringLiteral("pstyleXHigh"));
        sizePolicy1.setHeightForWidth(pstyleXHigh->sizePolicy().hasHeightForWidth());
        pstyleXHigh->setSizePolicy(sizePolicy1);
        pstyleXHigh->setMinimumSize(QSize(0, 26));

        gridLayout_2->addWidget(pstyleXHigh, 16, 0, 1, 2);

        pstyleData = new PStyleChooser(scrollAreaWidgetContents_4);
        pstyleData->setObjectName(QStringLiteral("pstyleData"));
        sizePolicy3.setHeightForWidth(pstyleData->sizePolicy().hasHeightForWidth());
        pstyleData->setSizePolicy(sizePolicy3);
        pstyleData->setMinimumSize(QSize(0, 26));

        gridLayout_2->addWidget(pstyleData, 4, 0, 1, 2);

        pstyleXLow = new PStyleChooser(scrollAreaWidgetContents_4);
        pstyleXLow->setObjectName(QStringLiteral("pstyleXLow"));
        sizePolicy3.setHeightForWidth(pstyleXLow->sizePolicy().hasHeightForWidth());
        pstyleXLow->setSizePolicy(sizePolicy3);
        pstyleXLow->setMinimumSize(QSize(0, 26));

        gridLayout_2->addWidget(pstyleXLow, 22, 0, 1, 2);

        labelLow = new QLabel(scrollAreaWidgetContents_4);
        labelLow->setObjectName(QStringLiteral("labelLow"));
        labelLow->setAlignment(Qt::AlignRight|Qt::AlignTrailing|Qt::AlignVCenter);

        gridLayout_2->addWidget(labelLow, 19, 0, 1, 1);

        labelName = new QLabel(scrollAreaWidgetContents_4);
        labelName->setObjectName(QStringLiteral("labelName"));
        labelName->setAlignment(Qt::AlignRight|Qt::AlignTrailing|Qt::AlignVCenter);

        gridLayout_2->addWidget(labelName, 14, 0, 1, 1);

        tableWidgetFormat = new QTableWidget(scrollAreaWidgetContents_4);
        if (tableWidgetFormat->columnCount() < 2)
            tableWidgetFormat->setColumnCount(2);
        QTableWidgetItem *__qtablewidgetitem = new QTableWidgetItem();
        tableWidgetFormat->setHorizontalHeaderItem(0, __qtablewidgetitem);
        QTableWidgetItem *__qtablewidgetitem1 = new QTableWidgetItem();
        tableWidgetFormat->setHorizontalHeaderItem(1, __qtablewidgetitem1);
        if (tableWidgetFormat->rowCount() < 2)
            tableWidgetFormat->setRowCount(2);
        QTableWidgetItem *__qtablewidgetitem2 = new QTableWidgetItem();
        tableWidgetFormat->setVerticalHeaderItem(0, __qtablewidgetitem2);
        QTableWidgetItem *__qtablewidgetitem3 = new QTableWidgetItem();
        tableWidgetFormat->setVerticalHeaderItem(1, __qtablewidgetitem3);
        tableWidgetFormat->setObjectName(QStringLiteral("tableWidgetFormat"));
        tableWidgetFormat->setVerticalScrollBarPolicy(Qt::ScrollBarAlwaysOff);
        tableWidgetFormat->setHorizontalScrollBarPolicy(Qt::ScrollBarAlwaysOff);
        tableWidgetFormat->setShowGrid(true);
        tableWidgetFormat->horizontalHeader()->setStretchLastSection(true);
        tableWidgetFormat->verticalHeader()->setVisible(false);

        gridLayout_2->addWidget(tableWidgetFormat, 10, 1, 1, 1);

        pstyleSelected = new PStyleChooser(scrollAreaWidgetContents_4);
        pstyleSelected->setObjectName(QStringLiteral("pstyleSelected"));
        sizePolicy3.setHeightForWidth(pstyleSelected->sizePolicy().hasHeightForWidth());
        pstyleSelected->setSizePolicy(sizePolicy3);

        gridLayout_2->addWidget(pstyleSelected, 12, 1, 1, 1);

        pushButtonRemove = new QPushButton(scrollAreaWidgetContents_4);
        pushButtonRemove->setObjectName(QStringLiteral("pushButtonRemove"));
        sizePolicy1.setHeightForWidth(pushButtonRemove->sizePolicy().hasHeightForWidth());
        pushButtonRemove->setSizePolicy(sizePolicy1);

        gridLayout_2->addWidget(pushButtonRemove, 23, 0, 1, 2);

        labelLowWord = new QLabel(scrollAreaWidgetContents_4);
        labelLowWord->setObjectName(QStringLiteral("labelLowWord"));

        gridLayout_2->addWidget(labelLowWord, 9, 0, 1, 1);

        lineEditLowWord = new QLineEdit(scrollAreaWidgetContents_4);
        lineEditLowWord->setObjectName(QStringLiteral("lineEditLowWord"));

        gridLayout_2->addWidget(lineEditLowWord, 9, 1, 1, 1);

        scrollArea->setWidget(scrollAreaWidgetContents_4);

        verticalLayout->addWidget(scrollArea);

        dockConfigure->setWidget(dockWidgetContents_2);
        PMainWindow->addDockWidget(static_cast<Qt::DockWidgetArea>(2), dockConfigure);
        toolBar = new QToolBar(PMainWindow);
        toolBar->setObjectName(QStringLiteral("toolBar"));
        PMainWindow->addToolBar(Qt::TopToolBarArea, toolBar);
        dockLink = new QDockWidget(PMainWindow);
        dockLink->setObjectName(QStringLiteral("dockLink"));
        sizePolicy.setHeightForWidth(dockLink->sizePolicy().hasHeightForWidth());
        dockLink->setSizePolicy(sizePolicy);
        dockLink->setMinimumSize(QSize(162, 235));
        dockWidgetContents_4 = new QWidget();
        dockWidgetContents_4->setObjectName(QStringLiteral("dockWidgetContents_4"));
        gridLayout_3 = new QGridLayout(dockWidgetContents_4);
        gridLayout_3->setObjectName(QStringLiteral("gridLayout_3"));
        lineEditIridium = new QLineEdit(dockWidgetContents_4);
        lineEditIridium->setObjectName(QStringLiteral("lineEditIridium"));

        gridLayout_3->addWidget(lineEditIridium, 5, 1, 1, 1);

        radioButtonHighGain = new QRadioButton(dockWidgetContents_4);
        radioButtonHighGain->setObjectName(QStringLiteral("radioButtonHighGain"));
        QSizePolicy sizePolicy4(QSizePolicy::Fixed, QSizePolicy::Fixed);
        sizePolicy4.setHorizontalStretch(0);
        sizePolicy4.setVerticalStretch(0);
        sizePolicy4.setHeightForWidth(radioButtonHighGain->sizePolicy().hasHeightForWidth());
        radioButtonHighGain->setSizePolicy(sizePolicy4);

        gridLayout_3->addWidget(radioButtonHighGain, 2, 0, 1, 1);

        radioButtonLOS = new QRadioButton(dockWidgetContents_4);
        radioButtonLOS->setObjectName(QStringLiteral("radioButtonLOS"));
        sizePolicy4.setHeightForWidth(radioButtonLOS->sizePolicy().hasHeightForWidth());
        radioButtonLOS->setSizePolicy(sizePolicy4);
        radioButtonLOS->setChecked(true);

        gridLayout_3->addWidget(radioButtonLOS, 0, 0, 1, 1);

        lineEditLOS = new QLineEdit(dockWidgetContents_4);
        lineEditLOS->setObjectName(QStringLiteral("lineEditLOS"));

        gridLayout_3->addWidget(lineEditLOS, 0, 1, 1, 1);

        radioButtonTDRSSOmni = new QRadioButton(dockWidgetContents_4);
        radioButtonTDRSSOmni->setObjectName(QStringLiteral("radioButtonTDRSSOmni"));
        sizePolicy4.setHeightForWidth(radioButtonTDRSSOmni->sizePolicy().hasHeightForWidth());
        radioButtonTDRSSOmni->setSizePolicy(sizePolicy4);

        gridLayout_3->addWidget(radioButtonTDRSSOmni, 3, 0, 1, 1);

        lineEditTDRSSOmni = new QLineEdit(dockWidgetContents_4);
        lineEditTDRSSOmni->setObjectName(QStringLiteral("lineEditTDRSSOmni"));

        gridLayout_3->addWidget(lineEditTDRSSOmni, 3, 1, 1, 1);

        radioButtonIridium = new QRadioButton(dockWidgetContents_4);
        radioButtonIridium->setObjectName(QStringLiteral("radioButtonIridium"));
        sizePolicy4.setHeightForWidth(radioButtonIridium->sizePolicy().hasHeightForWidth());
        radioButtonIridium->setSizePolicy(sizePolicy4);

        gridLayout_3->addWidget(radioButtonIridium, 5, 0, 1, 1);

        lineEditHighGain = new QLineEdit(dockWidgetContents_4);
        lineEditHighGain->setObjectName(QStringLiteral("lineEditHighGain"));

        gridLayout_3->addWidget(lineEditHighGain, 2, 1, 1, 1);

        radioButtonLoRate = new QRadioButton(dockWidgetContents_4);
        radioButtonLoRate->setObjectName(QStringLiteral("radioButtonLoRate"));
        sizePolicy4.setHeightForWidth(radioButtonLoRate->sizePolicy().hasHeightForWidth());
        radioButtonLoRate->setSizePolicy(sizePolicy4);

        gridLayout_3->addWidget(radioButtonLoRate, 7, 0, 1, 1);

        lineEditLoRate = new QLineEdit(dockWidgetContents_4);
        lineEditLoRate->setObjectName(QStringLiteral("lineEditLoRate"));

        gridLayout_3->addWidget(lineEditLoRate, 7, 1, 1, 1);

        pushButtonResetLink = new QPushButton(dockWidgetContents_4);
        pushButtonResetLink->setObjectName(QStringLiteral("pushButtonResetLink"));
        sizePolicy4.setHeightForWidth(pushButtonResetLink->sizePolicy().hasHeightForWidth());
        pushButtonResetLink->setSizePolicy(sizePolicy4);

        gridLayout_3->addWidget(pushButtonResetLink, 8, 0, 1, 1);

        verticalSpacer_2 = new QSpacerItem(20, 40, QSizePolicy::Minimum, QSizePolicy::Expanding);

        gridLayout_3->addItem(verticalSpacer_2, 9, 0, 1, 1);

        dockLink->setWidget(dockWidgetContents_4);
        PMainWindow->addDockWidget(static_cast<Qt::DockWidgetArea>(2), dockLink);
        dockWebServer = new QDockWidget(PMainWindow);
        dockWebServer->setObjectName(QStringLiteral("dockWebServer"));
        dockWebServerLayout = new QWidget();
        dockWebServerLayout->setObjectName(QStringLiteral("dockWebServerLayout"));
        formLayout = new QFormLayout(dockWebServerLayout);
        formLayout->setObjectName(QStringLiteral("formLayout"));
        verticalSpacer = new QSpacerItem(330, 20, QSizePolicy::Minimum, QSizePolicy::Expanding);

        formLayout->setItem(2, QFormLayout::FieldRole, verticalSpacer);

        spinBoxServerPort = new QSpinBox(dockWebServerLayout);
        spinBoxServerPort->setObjectName(QStringLiteral("spinBoxServerPort"));
        spinBoxServerPort->setMinimum(0);
        spinBoxServerPort->setMaximum(1000000000);

        formLayout->setWidget(1, QFormLayout::FieldRole, spinBoxServerPort);

        checkBoxServer = new QCheckBox(dockWebServerLayout);
        checkBoxServer->setObjectName(QStringLiteral("checkBoxServer"));

        formLayout->setWidget(1, QFormLayout::LabelRole, checkBoxServer);

        dockWebServer->setWidget(dockWebServerLayout);
        PMainWindow->addDockWidget(static_cast<Qt::DockWidgetArea>(2), dockWebServer);

        toolBar->addAction(actionLoad);
        toolBar->addAction(actionSave);
        toolBar->addAction(actionSaveAs);
        toolBar->addSeparator();
        toolBar->addAction(actionReset);
        toolBar->addSeparator();
        toolBar->addAction(actionConfigure);
        toolBar->addAction(actionLink);
        toolBar->addSeparator();
        toolBar->addAction(actionServer_Options);

        retranslateUi(PMainWindow);
        QObject::connect(actionConfigure, SIGNAL(triggered(bool)), dockConfigure, SLOT(setVisible(bool)));
        QObject::connect(dockConfigure, SIGNAL(visibilityChanged(bool)), actionConfigure, SLOT(setChecked(bool)));
        QObject::connect(actionLink, SIGNAL(triggered(bool)), dockLink, SLOT(setVisible(bool)));
        QObject::connect(dockLink, SIGNAL(visibilityChanged(bool)), actionLink, SLOT(setChecked(bool)));
        QObject::connect(actionServer_Options, SIGNAL(triggered(bool)), dockWebServer, SLOT(setVisible(bool)));
        QObject::connect(dockWebServer, SIGNAL(visibilityChanged(bool)), actionServer_Options, SLOT(setChecked(bool)));
        QObject::connect(checkBoxServer, SIGNAL(toggled(bool)), spinBoxServerPort, SLOT(setEnabled(bool)));

        QMetaObject::connectSlotsByName(PMainWindow);
    } // setupUi

    void retranslateUi(QMainWindow *PMainWindow)
    {
        PMainWindow->setWindowTitle(QApplication::translate("PMainWindow", "MainWindow", Q_NULLPTR));
        actionConfigure->setText(QApplication::translate("PMainWindow", "Configure", Q_NULLPTR));
#ifndef QT_NO_TOOLTIP
        actionConfigure->setToolTip(QApplication::translate("PMainWindow", "Edit Mode (Ctrl-E)", Q_NULLPTR));
#endif // QT_NO_TOOLTIP
#ifndef QT_NO_SHORTCUT
        actionConfigure->setShortcut(QApplication::translate("PMainWindow", "Ctrl+E", Q_NULLPTR));
#endif // QT_NO_SHORTCUT
        actionLink->setText(QApplication::translate("PMainWindow", "Link", Q_NULLPTR));
#ifndef QT_NO_TOOLTIP
        actionLink->setToolTip(QApplication::translate("PMainWindow", "Select the data source (Clrl-L)", Q_NULLPTR));
#endif // QT_NO_TOOLTIP
#ifndef QT_NO_SHORTCUT
        actionLink->setShortcut(QApplication::translate("PMainWindow", "Ctrl+L", Q_NULLPTR));
#endif // QT_NO_SHORTCUT
        actionSave->setText(QApplication::translate("PMainWindow", "Save", Q_NULLPTR));
#ifndef QT_NO_TOOLTIP
        actionSave->setToolTip(QApplication::translate("PMainWindow", "Save (Ctrl-S)", Q_NULLPTR));
#endif // QT_NO_TOOLTIP
#ifndef QT_NO_SHORTCUT
        actionSave->setShortcut(QApplication::translate("PMainWindow", "Ctrl+S", Q_NULLPTR));
#endif // QT_NO_SHORTCUT
        actionSaveAs->setText(QApplication::translate("PMainWindow", "Save As", Q_NULLPTR));
        actionLoad->setText(QApplication::translate("PMainWindow", "Load", Q_NULLPTR));
        actionHelp->setText(QApplication::translate("PMainWindow", "Help", Q_NULLPTR));
        actionReset->setText(QApplication::translate("PMainWindow", "Reset", Q_NULLPTR));
#ifndef QT_NO_TOOLTIP
        actionReset->setToolTip(QApplication::translate("PMainWindow", "Reset Link (CTRL-R)", Q_NULLPTR));
#endif // QT_NO_TOOLTIP
#ifndef QT_NO_SHORTCUT
        actionReset->setShortcut(QApplication::translate("PMainWindow", "Ctrl+R", Q_NULLPTR));
#endif // QT_NO_SHORTCUT
        actionServer_Options->setText(QApplication::translate("PMainWindow", "Server Options", Q_NULLPTR));
        dockConfigure->setWindowTitle(QApplication::translate("PMainWindow", "Edit", Q_NULLPTR));
        label->setText(QApplication::translate("PMainWindow", "Drag to insert", Q_NULLPTR));

        const bool __sortingEnabled = listWidgetInsertReal->isSortingEnabled();
        listWidgetInsertReal->setSortingEnabled(false);
        QListWidgetItem *___qlistwidgetitem = listWidgetInsertReal->item(0);
        ___qlistwidgetitem->setText(QApplication::translate("PMainWindow", "Box", Q_NULLPTR));
        QListWidgetItem *___qlistwidgetitem1 = listWidgetInsertReal->item(1);
        ___qlistwidgetitem1->setText(QApplication::translate("PMainWindow", "Number", Q_NULLPTR));
        QListWidgetItem *___qlistwidgetitem2 = listWidgetInsertReal->item(2);
        ___qlistwidgetitem2->setText(QApplication::translate("PMainWindow", "Multi", Q_NULLPTR));
        QListWidgetItem *___qlistwidgetitem3 = listWidgetInsertReal->item(3);
        ___qlistwidgetitem3->setText(QApplication::translate("PMainWindow", "Date/Time", Q_NULLPTR));
        QListWidgetItem *___qlistwidgetitem4 = listWidgetInsertReal->item(4);
        ___qlistwidgetitem4->setText(QApplication::translate("PMainWindow", "Dirfile name", Q_NULLPTR));
        QListWidgetItem *___qlistwidgetitem5 = listWidgetInsertReal->item(5);
        ___qlistwidgetitem5->setText(QApplication::translate("PMainWindow", "BitMulti", Q_NULLPTR));
        QListWidgetItem *___qlistwidgetitem6 = listWidgetInsertReal->item(6);
        ___qlistwidgetitem6->setText(QApplication::translate("PMainWindow", "Owl Animation", Q_NULLPTR));
        listWidgetInsertReal->setSortingEnabled(__sortingEnabled);

        label_2->setText(QApplication::translate("PMainWindow", "Configure", Q_NULLPTR));
        lineEditHighWord->setPlaceholderText(QApplication::translate("PMainWindow", "1111111111111111", Q_NULLPTR));
        labelSource->setText(QApplication::translate("PMainWindow", "Source", Q_NULLPTR));
        labelNBits->setText(QApplication::translate("PMainWindow", "# Bits", Q_NULLPTR));
        labelHighWord->setText(QApplication::translate("PMainWindow", "Hi Format", Q_NULLPTR));
        labelFormat_num->setText(QApplication::translate("PMainWindow", "Format:", Q_NULLPTR));
        labelType->setText(QApplication::translate("PMainWindow", "Type:", Q_NULLPTR));
        labelCurRow->setText(QApplication::translate("PMainWindow", "Selected:", Q_NULLPTR));
        labelExtrema->setText(QApplication::translate("PMainWindow", "Extrema:", Q_NULLPTR));
        pushButtonAddFormat->setText(QApplication::translate("PMainWindow", "New row", Q_NULLPTR));
        pushButtonDelFormat->setText(QApplication::translate("PMainWindow", "Del row", Q_NULLPTR));
        labelHigh->setText(QApplication::translate("PMainWindow", "High:", Q_NULLPTR));
        labelFormat_multi->setText(QApplication::translate("PMainWindow", "Format:", Q_NULLPTR));
        comboBoxExtrema->clear();
        comboBoxExtrema->insertItems(0, QStringList()
         << QApplication::translate("PMainWindow", "No Extrema", Q_NULLPTR)
         << QApplication::translate("PMainWindow", "New Extrema", Q_NULLPTR)
        );
        labelXLow->setText(QApplication::translate("PMainWindow", "XLow:", Q_NULLPTR));
        comboBoxType->clear();
        comboBoxType->insertItems(0, QStringList()
         << QApplication::translate("PMainWindow", "Date/Time", Q_NULLPTR)
         << QApplication::translate("PMainWindow", "Multi", Q_NULLPTR)
         << QApplication::translate("PMainWindow", "Number", Q_NULLPTR)
        );
        labelCaption->setText(QApplication::translate("PMainWindow", "Caption:", Q_NULLPTR));
        labelXHigh->setText(QApplication::translate("PMainWindow", "XHigh:", Q_NULLPTR));
        labelLow->setText(QApplication::translate("PMainWindow", "Low:", Q_NULLPTR));
        labelName->setText(QApplication::translate("PMainWindow", "Name", Q_NULLPTR));
        QTableWidgetItem *___qtablewidgetitem = tableWidgetFormat->horizontalHeaderItem(0);
        ___qtablewidgetitem->setText(QApplication::translate("PMainWindow", "Value", Q_NULLPTR));
        QTableWidgetItem *___qtablewidgetitem1 = tableWidgetFormat->horizontalHeaderItem(1);
        ___qtablewidgetitem1->setText(QApplication::translate("PMainWindow", "Text", Q_NULLPTR));
        QTableWidgetItem *___qtablewidgetitem2 = tableWidgetFormat->verticalHeaderItem(0);
        ___qtablewidgetitem2->setText(QApplication::translate("PMainWindow", "New Row", Q_NULLPTR));
        QTableWidgetItem *___qtablewidgetitem3 = tableWidgetFormat->verticalHeaderItem(1);
        ___qtablewidgetitem3->setText(QApplication::translate("PMainWindow", "New Row", Q_NULLPTR));
        pushButtonRemove->setText(QApplication::translate("PMainWindow", "DELETE", Q_NULLPTR));
        labelLowWord->setText(QApplication::translate("PMainWindow", "Lo Format", Q_NULLPTR));
        lineEditLowWord->setPlaceholderText(QApplication::translate("PMainWindow", "0000000000000000", Q_NULLPTR));
        toolBar->setWindowTitle(QApplication::translate("PMainWindow", "toolBar", Q_NULLPTR));
        dockLink->setWindowTitle(QApplication::translate("PMainWindow", "Link", Q_NULLPTR));
        lineEditIridium->setText(QApplication::translate("PMainWindow", "/data/etc/dialup.lnk", Q_NULLPTR));
        radioButtonHighGain->setText(QApplication::translate("PMainWindow", "Pilot", Q_NULLPTR));
        radioButtonLOS->setText(QApplication::translate("PMainWindow", "LOS", Q_NULLPTR));
        lineEditLOS->setText(QApplication::translate("PMainWindow", "/data/etc/defile.lnk", Q_NULLPTR));
        radioButtonTDRSSOmni->setText(QApplication::translate("PMainWindow", "TDRSS", Q_NULLPTR));
        lineEditTDRSSOmni->setText(QApplication::translate("PMainWindow", "/data/etc/tdrss.lnk", Q_NULLPTR));
        radioButtonIridium->setText(QApplication::translate("PMainWindow", "Dialup", Q_NULLPTR));
        lineEditHighGain->setText(QApplication::translate("PMainWindow", "/data/etc/pilot.lnk", Q_NULLPTR));
        radioButtonLoRate->setText(QApplication::translate("PMainWindow", "Packets", Q_NULLPTR));
        lineEditLoRate->setText(QApplication::translate("PMainWindow", "/data/etc/packets.lnk", Q_NULLPTR));
        pushButtonResetLink->setText(QApplication::translate("PMainWindow", "Reset Link", Q_NULLPTR));
        dockWebServer->setWindowTitle(QApplication::translate("PMainWindow", "Web Server", Q_NULLPTR));
        checkBoxServer->setText(QApplication::translate("PMainWindow", "Enable on port", Q_NULLPTR));
    } // retranslateUi

};

namespace Ui {
    class PMainWindow: public Ui_PMainWindow {};
} // namespace Ui

QT_END_NAMESPACE

#endif // UI_PMAINWINDOW_H
