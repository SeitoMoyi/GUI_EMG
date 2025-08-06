% Author- Nikhil Verma
%Last updated: Jan 18,2023
% !"C:\Program Files\MATLAB\R20XXx\bin\matlab" -r "Decoder_Stim_GUI.mlapp"
% to open new matlab instance

function daq_data_streaming_with_GUI_SMA
close all
clear all
clc

% initialization
global handles
global dq
global Fs
global StartbuttonState
global StopbuttonState
global DF
global Num_ch_AI
global SubID 
global SCS_baseDir
global server
global fid_write
global Filename
global pathname
global OPfile
global Filestr
global TrlNum
global dqout
global EMG_CH
global meta_data
global meta_path
global metadata_filename
global OPfile_METADATA
global muscle_labels
global analog_input_labels
global analog_in_ch
global analog_in_labels
global fig_path
global muscle_names


meta_data = struct;
StartbuttonState = 0;
StopbuttonState = 0;
server = 'localhost:7111'; %Always Running Mesage Manager on DAQ PC


% CHECK FILENAMES
%##############################
%TrlNum = 00;    %change to the trial number tht will be recorded
SubID = 'swallow_JET'; %Change in GUI
Filestr = '20250721';
%##########################
%%************ Uncomment for RNEL and comment for CMU **************
VOP_baseDir = 'D:\GIT\VOP_stroke\dragonfly';
addpath('D:\GIT\dragonfly\lang\matlab') %Dragonfly location: HAS TO BE CHANGED BASED ON THE SYSTEM

clc
% disp('Please check the file path where the data is being saved')
% disp('Press CTRL+C to terminate  OR ANY KEY to continue')
beep()
% pause;
% pathname = 'D:\scs_testing\data\test';
pathname = uigetdir('D:\scs_testing\data', 'Select path to save the data');
meta_path = [pathname '\metadata'];
fig_path = [pathname '\figures'];
if ~exist(meta_path, 'dir')
    mkdir(meta_path)
end
if ~exist(fig_path, 'dir')
    mkdir(fig_path)
end

[TrlNum] = get_nxt_trialnb(pathname);
%********************************************************************


Fs = 2500;
analog_in_ch = [1:16];
analog_input_labels = ...
{'HUMAC 1 Direction', ...
'HUMAC 2 Velocity', ...
'HUMAC 3 Torque', ...
'HUMAC 4 Position', ...
'KINARM Task Start', ...
'KINARM Recording Start', ...
'KINARM Repetition Start', ...
'VICON Recording start/stop//Kinarm Reach', ...
'VICON frame capture//Kinarm Pull', ...
'Grip Trigger', ...
'Grip Dynomometer', ...
'Pinch Dynomometer', ...
'Arduino Trigger', ...
'Arduino Amplitude', ...
'Arduino Stim Active', ...
'TMS Trig OUT'};

%%%%%%%%%%% Uncomment for Trigno system
EMG_CH = [17,27,29,23,41,43,37,47,57,51,61,63,65,75,77,71];

%%%% NORMAL LABELS
% muscle_labels = { ...
%     'L-TRAP',...         %EMG ch 1
%     'L-A-DEL',...         %EMG ch 2
%     'L-TRI',...    %EMG ch 3
%     'L-BIC',...    %EMG ch 4
%     'L-BRACH',...         %EMG ch 5
%     'NC',...         %EMG ch 6
%     'NC',...    %EMG ch 7
%     'NC',...    %EMG ch 8
%     'NC',...    %EMG ch 9
%     'NC',...    %EMG ch 10
%     'L-ED',...         %EMG ch 11 11A
%     'L-FD',...         %EMG ch 12 12A
%     'NC',...          %EMG ch 13
%     'NC',...          %EMG ch 14
%     'NC',...   %EMG ch 15 11B
%     'NC'       %EMG ch 16 12B
%     }; 
% 
% muscle_labels = { ...
%     'L-TRAP',...         %EMG ch 1
%     'L-A-DEL',...         %EMG ch 2
%     'L-TRI',...    %EMG ch 3
%     'L-BIC',...    %EMG ch 4
%     'L-BRACH',...         %EMG ch 5
%     'R-TRAP',...         %EMG ch 6
%     'R-A-DEL',...    %EMG ch 7
%     'R-TRI',...    %EMG ch 8
%     'R-BIC',...    %EMG ch 9
%     'R-BRACH',...    %EMG ch 10
%     'L-ED',...         %EMG ch 11 11A
%     'L-FD',...         %EMG ch 12 12A
%     'R-ED',...          %EMG ch 13
%     'R-FD',...          %EMG ch 14
%     'NC',...   %EMG ch 15 11B
%     'NC'       %EMG ch 16 12B
%     }; 


% muscle_labels = { ...
%     'Bicep',...         %EMG ch 1
%     'Flex',...         %EMG ch 2
%     'Ext',...    %EMG ch 3
%     'NC',...    %EMG ch 4
%     'NC',...         %EMG ch 5
%     'NC',...         %EMG ch 6
%     'NC',...    %EMG ch 7
%     'NC',...    %EMG ch 8
%     'APB',...    %EMG ch 9
%     'NC',...    %EMG ch 10
%     'NC',...         %EMG ch 11 11A
%     'NC',...         %EMG ch 12 12A
%     'opp-APB',...          %EMG ch 13
%     'NC',...          %EMG ch 14
%     'NC',...   %EMG ch 15 11B
%     'NC'       %EMG ch 16 12B
%     };     

% muscle_labels = { ...
%     'L-JAW',...           %EMG ch 1
%     'R-JAW',...         %EMG ch 2
%     'L-FLEX',...    %EMG ch 3
%     'L-CHEEK',...   %EMG ch 4
%     'R-FLEX',...   %EMG ch 5
%     'L-EXT',...         %EMG ch 6
%     'R-EXT',...         %EMG ch 7
%     'L-CHIN',...    %EMG ch 8
%     'R-CHEEK',...    %EMG ch 9
%     'NC',...    %EMG ch 10
%     'L-APB',...     %EMG ch 11
%     'L-FDI',...        %EMG ch 12
%     'R-CHIN',...          %EMG ch 13
%     'R-APB',...         %EMG ch 14
%     'R-FDI',...   %EMG ch 15 11B
%     'NC',...        %EMG ch 16 - 12B
%     }; 

% muscle_labels = { ...
%     'L-DEL',...         %EMG ch 1
%     'L-BI',...         %EMG ch 2
%     'L-TRI',...    %EMG ch 3
%     'L-FLEX',...    %EMG ch 4
%     'L-EXT',...    %EMG ch 5
%     'R-DEL',...         %EMG ch 6
%     'R-BI',...         %EMG ch 7
%     'R-TRI',...    %EMG ch 8
%     'R-FLEX',...    %EMG ch 9
%     'R-EXT',...    %EMG ch 10
%     'L-APB',...        %EMG ch 11
%     'R-APB',...        %EMG ch 12
%     'NC',...         %EMG ch 13
%     'NC',...         %EMG ch 14
%     'L-FDI',...   %EMG ch 15 11B
%     'R-FDI'...        %EMG ch 16 - 12B
%     }; 


% % Gallileo Labels
% % 8, 11 and 12 are minis
% muscle_labels = { ...
%     'L-TRAP-1',...         %EMG ch 1
%     'L-M-DEL-1',...         %EMG ch 2
%     'L-A-DEL',...    %EMG ch 3
%     'L-BRACH-RAD',...    %EMG ch 4
%     'L-TRAP-2',...    %EMG ch 5
%     'L-M-DEL-2',...         %EMG ch 6
%     'L-BIC-MED',...         %EMG ch 7
%     'L-FCR',...    %EMG ch 8
%     'L-TRAP-3',...    %EMG ch 9
%     'L-M-DEL-3',...    %EMG ch 10
%     'L-TRI-MED',...      %EMG ch 11 11A
%     'L-ECR',...         %EMG ch 12 12A
%     'L-TRAP-4',...         %EMG ch 13
%     'L-M-DEL-4',...         %EMG ch 14
%     'NC',...   %EMG ch 15 11B
%     'NC'...        %EMG ch 16
%     }; 

% % Gallileo Labels FATTIGUE
% muscle_labels = { ...
%     'R-M-DEL-1',...         %EMG ch 1
%     'R-A-DEL-1',...         %EMG ch 2
%     'NC',...    %EMG ch 3
%     'NC',...    %EMG ch 4
%     'R-M-DEL-2',...    %EMG ch 5
%     'R-A-DEL-2',...         %EMG ch 6
%     'NC',...         %EMG ch 7
%     'NC',...    %EMG ch 8
%     'R-M-DEL-3',...    %EMG ch 9
%     'R-A-DEL-3',...    %EMG ch 10
%     'NC',...      %EMG ch 11 11A
%     'NC',...         %EMG ch 12 12A
%     'R-M-DEL-4',...         %EMG ch 13
%     'R-A-DEL-4',...         %EMG ch 14
%     'NC',...   %EMG ch 15 11B
%     'NC'...        %EMG ch 16
%     }; 

% % % Gallileo Labels PINCH
% muscle_labels = { ...
%     'L-APM-1',...         %EMG ch 1
%     'L-ECR-1',...         %EMG ch 2
%     'NC',...    %EMG ch 3
%     'NC',...    %EMG ch 4
%     'L-APM-2',...    %EMG ch 5
%     'L-ECR-2',...         %EMG ch 6
%     'NC',...         %EMG ch 7
%     'NC',...    %EMG ch 8
%     'L-APM-3',...    %EMG ch 9
%     'L-ECR-3',...    %EMG ch 10
%     'NC',...      %EMG ch 11 11A
%     'NC',...         %EMG ch 12 12A
%     'L-APM-4',...         %EMG ch 13
%     'L-ECR-4',...         %EMG ch 14
%     'NC',...   %EMG ch 15 11B
%     'NC'...        %EMG ch 16
%     }; 
% 
% % % Gallileo Labels KINARM
% muscle_labels = { ...
%     'R-P-DEL-1',...         %EMG ch 1
%     'R-M-DEL-1',...         %EMG ch 2
%     'R-ECR',...    %EMG ch 3
%     'L-M-DEL',...    %EMG ch 4
%     'R-P-DEL-2',...    %EMG ch 5
%     'R-M-DEL-2',...         %EMG ch 6
%     'R-BRACH-RAD',...         %EMG ch 7
%     'L-BRACH-RAD',...    %EMG ch 8
%     'R-P-DEL-3',...    %EMG ch 9
%     'R-M-DEL-3',...    %EMG ch 10
%     'R-BIC-MED',...      %EMG ch 11 11A
%     'R-TRI-MED',...         %EMG ch 12 12A
%     'R-P-DEL-4',...         %EMG ch 13
%     'R-M-DEL-4',...         %EMG ch 14
%     'L-BIC-MED',...   %EMG ch 15 11B
%     'L-TRI-MED'...        %EMG ch 16
%     }; 

% muscle_labels = { ...
%     'Emg1',...         %EMG ch 1
%     'Emg2',...         %EMG ch 2
%     'Emg3',...    %EMG ch 3
%     'Emg4',...    %EMG ch 4
%     'Emg5',...    %EMG ch 5
%     'Emg6',...         %EMG ch 6
%     'Emg7',...         %EMG ch 7
%     'NC',...    %EMG ch 8
%     'NC',...    %EMG ch 9
%     'NC',...    %EMG ch 10
%     'NC',...      %EMG ch 11 11A
%     'NC',...         %EMG ch 12 12A
%     'NC',...         %EMG ch 13
%     'NC',...         %EMG ch 14
%     'NC',...   %EMG ch 15 11B
%     'NC'...        %EMG ch 16
%     }; 

% %%%% NORMAL LABELS
% muscle_labels = { ...
%     'R-TRAP',...         %EMG ch 1
%     'R-M-DEL',...         %EMG ch 2
%     'NC',...    %EMG ch 3
%     'NC',...    %EMG ch 4
%     'R-BRACH-RAD',...    %EMG ch 5
%     'L-TRAP',...         %EMG ch 6
%     'L-M-DEL',...         %EMG ch 7
%     'L-P-DEL',...    %EMG ch 8
%     'R-P-DEL',...    %EMG ch 9
%     'L-BRACH-RAD',...    %EMG ch 10
%     'R-BIC-MED',...        %EMG ch 11
%     'L-BIC-MED',...        %EMG ch 12
%     'STIM',...         %EMG ch 13
%     'NC',...         %EMG ch 14
%     'R-TRI-MED',...   %EMG ch 15 11B
%     'L-TRI-MED'...        %EMG ch 16
%     }; 
% %%%% NORMAL LABES
% muscle_labels = { ...
%     'R-TRAP',...         %EMG ch 1
%     'R-M-DEL',...         %EMG ch 2
%     'R-BIC-MED',...    %EMG ch 3
%     'R-TRI-MED',...    %EMG ch 4
%     'R-BRACH-RAD',...    %EMG ch 5
%     'L-TRAP',...         %EMG ch 6
%     'L-M-DEL',...         %EMG ch 7
%     'L-BIC-MED',...    %EMG ch 8
%     'L-TRI-MED',...    %EMG ch 9
%     'L-BRACH-RAD',...    %EMG ch 10
%     'R-FCR',...        %EMG ch 11
%     'L-FCR',...        %EMG ch 12
%     'NC',...         %EMG ch 13
%     'NC',...         %EMG ch 14
%     'R-ECR',...   %EMG ch 15 11B
%     'L-ECR'...        %EMG ch 16
%     }; 
% 
%%%% NORMAL LABELS
% muscle_labels = { ...
%     'R-TRAP',...         %EMG ch 1
%     'R-M-DEL',...         %EMG ch 2
%     'R-BIC-MED',...    %EMG ch 3
%     'R-TRI-MED',...    %EMG ch 4
%     'R-BRACH-RAD',...    %EMG ch 5
%     'L-TRAP',...         %EMG ch 6
%     'L-M-DEL',...         %EMG ch 7
%     'L-BIC-MED',...    %EMG ch 8
%     'L-TRI-MED',...    %EMG ch 9
%     'L-BRACH-RAD',...    %EMG ch 10
%     'R-FCR',...        %EMG ch 11
%     'L-FCR',...        %EMG ch 12
%     'R-APB',...         %EMG ch 13
%     'L-APB',...         %EMG ch 14
%     'R-ECR',...   %EMG ch 15 11B
%     'L-ECR'...        %EMG ch 16
%     }; 

% % % %%%% TMS LABES
% muscle_labels = { ...
%     'R-A-DEL',...         %EMG ch 1
%     'R-BIC-MED',...    %EMG ch 2
%     'R-TRI-MED',...    %EMG ch 3
%     'R-BRACH-RAD',...    %EMG ch 4
%     'L-A-DEL',...         %EMG ch 5
%     'L-BIC-MED',...    %EMG ch 6
%     'L-TRI-MED',...    %EMG ch 7
%     'L-BRACH-RAD',... %EMG ch 8
%     'R-ECR',...          %EMG ch 9
%     'L-ECR',...        %EMG ch 10
%     'N/A',...        %EMG ch 11 11A
%     'N/A',...         %EMG ch 12 12A ## CHANGE BACK TO RIGHT
%     'R-FCR',...         %EMG ch 13 ## CHANGE BACK TO LEFT
%     'L-FCR',...   %EMG ch 14 11B
%     'R-FDM'...        %EMG ch 15 11B
%     'L-FDM'...        %EMG ch 16 12B
%     }; 

muscle_labels = { ...
    'L_APB',...         %EMG ch 1
    'NC',...         %EMG ch 2
    'L-FLEX',...    %EMG ch 3
    'L_FDI',...    %EMG ch 4
    'NC',...         %EMG ch 5
    'NC',...         %EMG ch 6
    'NC',...    %EMG ch 7
    'NC',...    %EMG ch 8
    'NC',...    %EMG ch 9 9A
    'NC',...    %EMG ch 10
    'NC',...         %EMG ch 11 11A
    'NC',...         %EMG ch 12 12A
    'NC',...          %EMG ch 13 9B
    'NC',...          %EMG ch 14
    'NC',...   %EMG ch 15 11B
    'NC'
    };     %EMG ch 16 12B

muscle_names = get_muscle_names(muscle_labels);

extra_lab = length(EMG_CH)-length(muscle_labels);
if ~(extra_lab==0)
    error(sprintf('ERROR: Muscle labels not equal to EMG channel number\n  Add %d blank labels at the end of Muscle Labels',extra_lab))
    return
end

if rem(length(EMG_CH),2)==0
    Nplots = length(EMG_CH);
else
    fprintf('Current number of EMG channels = %d\n',length(EMG_CH))
    error('Please add even number of EMG channels')
end

% meta data initialisation

meta_data.sub_id = SubID;
meta_data.date = date;
meta_data.timestamp =  datestr(now,'HHMMSS');
meta_data.exp_name = Filestr;
meta_data.trl_num = TrlNum;
meta_data.fs = Fs;
meta_data.total_num_emg_ch = length(muscle_labels); % tentative
meta_data.emg_ch_number = EMG_CH;
meta_data.musc_labels = muscle_labels;
meta_data.musc_names = muscle_names;
meta_data.updaterate = 0.1;
meta_data.updaterate_unit = 'seconds';
meta_data.stim = 0;
meta_data.analog_input_labels = analog_input_labels;
meta_data.analog_in_ch = analog_in_ch;
meta_data.pulse_width = 200;
meta_data.pulse_width_unit = 'micro_seconds';
meta_data.duty_cycle = 100;
meta_data.dutycycle_unit = 'percent';

%% Make GUI

handles = struct;
% delete any existing instruments on startup
delete(instrfind) %cleaning things
handles.MainWindow = figure('Name','DAQ_Recording_GUI','Position',...
    [680 731 454 260],'MenuBar','none', 'NumberTitle','Off', 'Resize',...
    'On', 'Toolbar','none','Visible', 'On');
% handles.LeftPanel= uipanel('Parent',handles.MainWindow,'BorderType','none',...
%     'Units','normalized','Position',[0 0 0.5 1]);
% check that DAQ is connected and recongnized by computer
handles.daqdisplay = uicontrol('Parent',handles.MainWindow,'Style','text',...
    'Position',[129 34 201 51],...
    'FontSize',11,'String',[]);
handles.Refresh = uicontrol('Parent',handles.MainWindow,'Style','pushbutton','Position',[135 98 186 37],...
    'String','Reconnect','fontsize',12,...
    'Callback',{@refreshDAQ});
% handles.sendEMGConfig = uicontrol('Parent',handles.MainWindow,'Style','pushbutton','Position',[29 98 186 37],...
%     'String','Send EMG Config','fontsize',12,'BackgroundColor',[0.55, 0.01, 0],'enable','off',...
%     'Callback',{@SendEMGConfig});
handles.StartStim = uicontrol('Parent',handles.MainWindow,'Style','pushbutton','Position',[33 161 168 74],...
    'String','START','FontSize',28,'Callback',{@startRec});
handles.StopStim = uicontrol('Parent',handles.MainWindow,'Style','pushbutton','Position',[250 161 168 74],...
    'String','STOP','FontSize',28,...
    'Callback',{@stopRec});

set(handles.MainWindow,'Color',[0.55, 0.01, 0]); 
set(handles.daqdisplay,'backgroundcolor',get(handles.MainWindow,'color')); 
set(handles.StartStim,'BackgroundColor',[0.55, 0.01, 0])
set(handles.StopStim,'BackgroundColor',[0.55, 0.01, 0])
set(handles.Refresh,'BackgroundColor',[0.55, 0.01, 0])

refreshDAQ

%% Callback functions
    function SendEMGConfig(~,~)
        if StartbuttonState == 0
            running = true;
            configstr = 'Waiting for Plot Request';
            set(handles.daqdisplay,'String',configstr)
            while running
                disp 'Waiting for EMG Config request'
                M = ReadMessage(1);
                if ~isempty(M)
                    switch M.msg_type
                        case 'SCS_REQUEST'
                            msg = DF.MDF.SCS_EMG_CONFIG;
                            DF.defines.SCS_MAX_EMG_CHANS = length(Num_ch_AI);
                            SendMessage( 'SCS_EMG_CONFIG', msg);
                            configstr = 'Sent EMG Config';
                            set(handles.daqdisplay,'String',configstr)
                            running = false;
                    end
                end
            end
            
        end
    end

    function refreshDF
        DisconnectFromMMM();
        MessageTypes =  { 'SCS_REQUEST' };
        try
            ConnectToMMM(0, SCS_baseDir, fullfile(SCS_baseDir, 'SCS_SMA_message_defs.mat'), ['-server_name ' server]); % 0 will be our module ID
            disp('Connected.');
        catch ME
            error( ['Could not connect to Message Manager at ' server] );
        end
        Subscribe( MessageTypes{:})
        
        disp 'Connected to Message manager'
    end

    function refreshDAQ(~,~)
        refreshDF
        daqreset
        DF.defines.SCS_EMG_FS = Fs;
        d = daqlist("ni")
        if isempty(d)
%             daqstr = 'No DAQ Available';
            daqstr = sprintf('No DAQ Available\nLast Trial no: %d\nNext Trial no: %d', TrlNum-1, TrlNum);
        else
%             daqstr = 'DAQ successfully connected';
            daqstr = sprintf('DAQ successfully connected\nLast Trial no: %d\nNext Trial no: %d', TrlNum-1, TrlNum);
        end
        set(handles.daqdisplay,'String',daqstr);
        deviceInfo = d{1, "DeviceInfo"};        % uncomment for device info
        
%         dqout = daq("ni");
        dq = daq("ni");
        dq.Rate = Fs;
        ME = [];
        try
            ANA_IN_params = addinput(dq, "Dev1", 0:15, "Voltage");
            ANA_IN_EMG = addinput(dq, "Dev1", 16:79, "Voltage");            % EMG channels 1:6 from Bagnoli
            Num_ch_AI = length(ANA_IN_params)+length(ANA_IN_EMG);
            meta_data.total_analog_in_ch = Num_ch_AI;
            
%             Dout1 = addoutput(dqout,"Dev1","Port1/Line1","Digital");
%             Dout2 = addoutput(dqout,"Dev1","Port1/Line2","Digital");
            
            
            for i= 1:length(ANA_IN_params)
                ANA_IN_params(i).TerminalConfig =  'SingleEndedNonReferenced'; % If signal is grounded %'SingleEndedNonReferenced'; If signal is not grounded
                %                 ANA_IN_params(i).Coupling = 'AC';
            end
            for i= 1:length(ANA_IN_EMG)
                ANA_IN_EMG(i).TerminalConfig = 'SingleEnded';
                %                 ANA_IN_EMG(i).Coupling = 'AC';
            end
        catch ME
            daqstr = 'No DAQ Available';
            set(handles.daqdisplay,'String',daqstr);
        end
        if isempty(ME)
%             daqstr = 'DAQ successfully connected';
            daqstr = sprintf('DAQ successfully connected\nLast Trial no: %d\nNext Trial no: %d', TrlNum-1, TrlNum);
            set(handles.daqdisplay,'String',daqstr);
            set(handles.MainWindow,'Color',[0.94 0.94 0.94]); 
            set(handles.daqdisplay,'backgroundcolor',get(handles.MainWindow,'color'));
            set(handles.StartStim,'BackgroundColor',[0.21, 0.49, 0.42])
            set(handles.StopStim,'BackgroundColor',[0.55, 0.01, 0])
            set(handles.Refresh,'BackgroundColor',[0.55, 0.01, 0])
        end
    end

    function startRec(~,~)
        set(handles.StartStim,'BackgroundColor',[0.55, 0.01, 0])
        set(handles.StopStim,'BackgroundColor',[0.21, 0.49, 0.42])
        set(handles.Refresh,'BackgroundColor',[0.55, 0.01, 0])
        
        clc
        tic
        StopbuttonState = 0;
        if (exist('dq','var') && ~isempty(dq))
            StartbuttonState = 1;
            Filename = [datestr(now,'yyyymmdd_HHMMSS_'),SubID,'_',Filestr,'_',sprintf('Trl%s.bin',num2str(TrlNum,'%03.f'))]; %Change in GUI
            metadata_filename = [datestr(now,'yyyymmdd_HHMMSS_'),SubID,'_',Filestr,'_METADATA',sprintf('Trl%s.mat',num2str(TrlNum,'%03.f'))]; %Change in GUI
            OPfile = fullfile(pathname, Filename);
            OPfile_METADATA = fullfile(meta_path, metadata_filename);
            
            fid_write = fopen(OPfile,"a"); %to append data in a file
            
            %% ##########################
            dq.ScansAvailableFcnCount = meta_data.updaterate*Fs;
            %% ##########################
            dq.ScansAvailableFcn = @(src, evt) logNbroadcastData(src, evt, fid_write);
            fprintf('\nOutput File Generated:  %s at \n %s\n',Filename,pathname);
            pause(2)
            
%             write(dqout,[1 0])
            start(dq,'Continuous')
            
%             recstr = 'Recording...';
%             set(handles.daqdisplay,'String',recstr);
            
            set(handles.MainWindow,'Color',[0.94 0.94 0.94]); 
            set(handles.daqdisplay,'backgroundcolor',get(handles.MainWindow,'color'));
            set(handles.StartStim,'BackgroundColor',[0.55, 0.01, 0])
            set(handles.StopStim,'BackgroundColor',[0.21, 0.49, 0.42])
            set(handles.Refresh,'BackgroundColor',[0.55, 0.01, 0])
            
            recstr = 'Recording...';
            set(handles.daqdisplay,'String',recstr);
            get(handles.daqdisplay, 'Value');
            set(handles.daqdisplay,'ForegroundColor','k');            
            
            while dq.Running
                pause(1)
                if StopbuttonState == 1
                    if (exist('dq','var') && ~isempty(dq))
                        stop(dq)
%                         write(dqout,[0 1])
                        pause(0.001)
                    end
                end
            end
        else
            error('Please Reconnect to DAQ')
        end
    end

    function logNbroadcastData(src, ~, fid)
        %% save and plot recorded data
        [data, timestamps, ~] = read(src, src.ScansAvailableFcnCount, "OutputFormat", "Matrix");
        fwrite(fid,[timestamps, data]','double');
        data_1d = data(:,[1:16,EMG_CH]);
        data_1d = data_1d(:);
        %% send data to Dragonfly
        DF.defines.SCS_EMG_SAMPLES_PER_MSG   = length(timestamps);
        DF.defines.TrialNumber   = TrlNum;
        msg = DF.MDF.SCS_EMG_DATA_DIFF;
        msg.source_timestamp = timestamps';
        msg.data = data_1d';
        SendMessage( 'SCS_EMG_DATA_DIFF', msg);
        fprintf('Sent message to Dragonfly\n');
        timeElapsed = sprintf('\t\t\tTrial no: %d\nElapsed time is %f seconds',TrlNum,toc);
        set(handles.daqdisplay,'String',timeElapsed);
        drawnow
    end

    function stopRec(~,~)
        set(handles.StartStim,'BackgroundColor',[0.55, 0.01, 0])
        set(handles.StopStim,'BackgroundColor',[0.55, 0.01, 0])
        set(handles.Refresh,'BackgroundColor',[0.21, 0.49, 0.42])
        StartbuttonState = 0;
        StopbuttonState = 1;
        
        if isempty(dq)
            daqstr = 'DAQ not recording';
        else
            stop(dq)
%             write(dqout,[0 1])
%             stop(dqout)
%             flush(dqout)
            %             msg = DF.MDF.SCS_EXIT;
            %             SendMessage('SCS_EXIT',msg);
%             daqstr = sprintf('Trial no: %d\nAcquisition Terminated',TrlNum);
            daqstr = sprintf('Acquisition Terminated\nLast Trial no: %d\nNext Trial no: %d', TrlNum, TrlNum+1);
            set(handles.daqdisplay,'String',daqstr);
            drawnow
            fprintf("Trial no:%d\nAcquisition has terminated with %d scans acquired\n", TrlNum,dq.NumScansAcquired);
            flush(dq)
            fclose(fid_write);
            TrlNum = TrlNum+1;
            meta_data.sub_id = SubID;
            meta_data.date = date;
            meta_data.timestamp =  datestr(now,'HHMMSS');
            meta_data.exp_name = Filestr;
            meta_data.trl_num = TrlNum;
            meta_data.fs = Fs;
            meta_data.total_num_emg_ch = 10; % tentative
            meta_data.emg_ch_number = EMG_CH;
            
            %             meta_data.emg_ch_number_in_file = EMG_CH;
            save(OPfile_METADATA,'meta_data');
            
            pause(0.001)
            read_data_from_file()
            
        end
        
        DisconnectFromMMM();
    end

    function read_data_from_file
        %%read and plot data from file
        fid_read = fopen(OPfile,'r');
        [datareaD,count] = fread(fid_read,[Num_ch_AI+1,inf],'double');
        data_read_plots = zeros(Num_ch_AI,1);
        data_read__ax = zeros(Num_ch_AI,1);
        data_read_fig = figure(2);
        data_read_fig.WindowState = 'maximized';
        
        set(data_read_fig,'Color',[0 0 0])
        set(data_read_fig, 'position', [50 200 750 750])
        
        if rem(length(EMG_CH),2)==0
            Nplots = length(EMG_CH);
        else
            Nplots = length(EMG_CH)-1;
        end
        for j = 1:Nplots
            i = EMG_CH(j);
            data_read__ax(j) = subplot(16/2,2,j);
            data_read_plots(j) = plot(datareaD(1,:),datareaD(i+1,:),'-y','LineWidth',1);
            
            set(data_read__ax(j),'XGrid','on');
            set(data_read__ax(j),'XColor',[0.9725 0.9725 0.9725]);
            set(data_read__ax(j),'YColor',[0.9725 0.9725 0.9725]);
            set(data_read__ax(j),'Color',[.15 .15 .15]);
            set(data_read__ax(j),'YGrid','on');
            set(data_read__ax(j),'XGrid','on');
            set(data_read__ax(j),'YLim', [-1 1]);
            set(data_read__ax(j),'YLimMode', 'manual');
            
            title(sprintf('%i-%s', j,muscle_labels{j}),'Color',[0.9725 0.9725 0.9725]);
        end
%         linkaxes(data_read__ax,'x');
        
        
        
        
        
        data_read_plots2 = zeros(Num_ch_AI,1);
        data_read__ax2 = zeros(Num_ch_AI,1);
        data_read_fig2 = figure(3);
        data_read_fig2.WindowState = 'maximized';
        
        set(data_read_fig2,'Color',[0 0 0])
        set(data_read_fig2, 'position', [50 200 750 750])

        for j = 1:Nplots
            i = j;
            data_read__ax2(j) = subplot(16/2,2,j);
            %data_read_plots2(j) = plot(datareaD(1,:),datareaD(i+1,:),'-y','LineWidth',1);
            iData = datareaD(i+1,:);
            if i == 14
                iData = iData*20/10;
            end
            data_read_plots2(j) = plot(datareaD(1,:),iData,'-y','LineWidth',1);
            
            set(data_read__ax2(j),'XGrid','on');
            set(data_read__ax2(j),'XColor',[0.9725 0.9725 0.9725]);
            set(data_read__ax2(j),'YColor',[0.9725 0.9725 0.9725]);
            set(data_read__ax2(j),'Color',[.15 .15 .15]);
            set(data_read__ax2(j),'YGrid','on');
            set(data_read__ax2(j),'XGrid','on');
            set(data_read__ax2(j),'YLim', [-1 6]);
            set(data_read__ax2(j),'YLimMode', 'manual');
            
            title(sprintf('DAQ AI-%i', j-1),'Color',[0.9725 0.9725 0.9725]);
        end
%         linkaxes(data_read__ax2,'x');

%         saveas(gcf, ai_fig_filename);
        
        fclose(fid_read);
    end
end